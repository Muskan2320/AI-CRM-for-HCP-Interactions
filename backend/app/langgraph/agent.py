import json
import os
from dotenv import load_dotenv
from typing import TypedDict

from langgraph.graph import StateGraph
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from app.langgraph.tools import (
    search_hcp_tool,
    log_interaction_tool,
    edit_interaction_tool,
    get_pending_followups_tool,
    get_hcp_interaction_history_tool
)

# ---------------- LLM ---------------- #
load_dotenv()
llm = ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile",
    temperature=0.2
)

# ---------------- STATE ---------------- #

class AgentState(TypedDict):
    input: str
    plan: dict
    output: str

# ---------------- SYSTEM INSTRUCTION ---------------- #

SYSTEM_INSTRUCTION = """
You are an AI CRM assistant for managing doctor (HCP) interactions.

Your job:
- Understand user intent
- Select correct tool(s)
- Extract required and optional inputs
- Return execution steps in JSON

----------------------
AVAILABLE TOOLS
----------------------

1. search_hcp
Description:
Find doctor (HCP) details.

Required Inputs:
- NONE

Optional Inputs:
- name (string)
- hospital (string)
- hcp_id (int)

Use cases:
- Find doctor
- Get HCP ID before history

Output:
List of doctors with:
- hcp_id
- name
- hospital
- specialization
- city


2. log_interaction
Description:
Log a new interaction with a doctor.

Required Inputs:
- name (string)
- hospital (string)

Optional Inputs:
- notes (string)
- follow_up_action (string)
- follow_up_date (YYYY-MM-DD)

Use cases:
- User describes meeting or discussion

IMPORTANT:
Extract structured data from user sentence.


3. edit_interaction
Description:
Update an interaction.

Required Inputs:
- interaction_id (int)

Optional Inputs:
- notes
- follow_up_status (pending/completed/cancelled/no_follow_up)
- follow_up_date


4. get_pending_followups
Description:
Get pending follow-ups.

Required Inputs:
- NONE

Optional Inputs:
- NONE


5. get_hcp_interaction_history
Description:
Get interaction history of a doctor.

Required Inputs:
- hcp_id (int)

Optional Inputs:
- NONE


----------------------
RULES
----------------------

- ALWAYS return ONLY valid JSON
- NO explanation text
- NO extra text outside JSON
- Use correct tool name EXACTLY
- If required input missing → first get it using another tool
- If name is given but you need hcp_id for another tool:
  → first call search_hcp
  → then use $prev.hcp_id
  → only output fields are accessible for chaining, that are not present in user input

----------------------
OUTPUT FORMAT
----------------------

{
  "steps": [
    {
      "tool": "tool_name",
      "data": { }
    }
  ]
}
"""

# ---------------- TOOL MAP ---------------- #

TOOLS = {
    "search_hcp": search_hcp_tool,
    "log_interaction": log_interaction_tool,
    "edit_interaction": edit_interaction_tool,
    "get_pending_followups": get_pending_followups_tool,
    "get_hcp_interaction_history": get_hcp_interaction_history_tool
}

# ---------------- PLAN STEP ---------------- #

def create_plan(state: AgentState):
    user_input = state["input"]

    messages = [
        SystemMessage(content=SYSTEM_INSTRUCTION),
        HumanMessage(content=user_input)
    ]

    response = llm.invoke(messages)
    content = response.content.strip()

    print("\n--- RAW LLM ---")
    print(content)

    # Extract JSON safely
    start = content.find("{")
    end = content.rfind("}") + 1
    content = content[start:end]

    try:
        plan = json.loads(content)
    except:
        return {"output": "Invalid LLM response"}

    return {
        "plan": plan,
        "input": user_input
    }

# ---------------- EXECUTE STEP ---------------- #

def execute_plan(state: AgentState):
    plan = state.get("plan", {})
    steps = plan.get("steps", [])

    prev_result = None
    last_result = None

    for idx, step in enumerate(steps):
        tool_name = step.get("tool")
        data = step.get("data", {})

        tool = TOOLS.get(tool_name)

        if not tool:
            return {
                "error": True,
                "step": idx,
                "message": f"Unknown tool: {tool_name}",
                "plan": plan
            }

        # Handle chaining ($prev)
        for k, v in data.items():
            if isinstance(v, str) and "$prev." in v and prev_result:
                key = v.split(".")[1]
                data[k] = prev_result.get(key)

        try:
            result = tool(**data)
        except Exception as e:
            return {
                "error": True,
                "step": idx,
                "message": str(e),
                "failed_tool": tool_name,
                "data": data,
                "plan": plan
            }

        # Store result
        last_result = result

        # Update chaining
        if isinstance(result, list) and len(result) > 0:
            prev_result = result[0]
        elif isinstance(result, dict):
            prev_result = result

    return {"output": last_result}

def execute_with_retry(state: AgentState, max_retries=2):
    user_input = state["input"]
    plan = state.get("plan", {})

    for attempt in range(max_retries + 1):
        print(f"Retry attempt {attempt+1}")

        result = execute_plan({
            "plan": plan,
            "input": user_input
        })

        # SUCCESS
        if not result.get("error"):
            return result

        # FAILURE
        error_info = result

        print(f"\n--- RETRY {attempt+1} ---")
        print("Error:", error_info["message"])

        # stop if max retries reached
        if attempt == max_retries:
            return {
                "output": f"Failed after {max_retries} retries",
                "last_error": error_info["message"]
            }

        # Ask LLM to fix plan
        fix_prompt = f"""
The previous execution failed.

User request:
{user_input}

Error:
{error_info['message']}

Failed tool:
{error_info.get('failed_tool')}

Failed step index:
{error_info.get('step')}

Previous plan:
{json.dumps(plan)}

Fix the plan.

Rules:
- Keep valid steps unchanged
- Fix only the failing step
- Ensure required inputs are present
- DO NOT add unnecessary tools
- Also, names to be stored and fetched without prefix suffix like dr., hospital etc.

Return ONLY valid JSON:
{{
  "steps": [
    {{
      "tool": "tool_name",
      "data": {{}}
    }}
  ]
}}
"""

        messages = [
            SystemMessage(content=SYSTEM_INSTRUCTION),
            HumanMessage(content=fix_prompt)
        ]

        response = llm.invoke(messages)
        content = response.content.strip()

        # extract JSON safely
        start = content.find("{")
        end = content.rfind("}") + 1
        content = content[start:end]

        try:
            plan = json.loads(content)
        except:
            return {"output": "Failed to fix plan"}

    return {"output": "Execution failed"}

# ---------------- GRAPH ---------------- #

builder = StateGraph(AgentState)

builder.add_node("plan", create_plan)
builder.add_node("execute", execute_with_retry)

builder.set_entry_point("plan")
builder.add_edge("plan", "execute")
builder.set_finish_point("execute")

graph = builder.compile()