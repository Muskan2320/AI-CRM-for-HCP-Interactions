import json
import os
import re
from dotenv import load_dotenv
from typing import TypedDict
from datetime import date, timedelta

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
from app.logger import logger
from app.schemas import Plan

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

ALLOWED_PARAMS = {
    "search_hcp": {"hcp_id", "name", "hospital"},
    "log_interaction": {
        "name",
        "hospital",
        "topic",
        "specialization",
        "city",
        "interaction_date",
        "follow_up_action",
        "follow_up_date",
        "notes"
    },
    "edit_interaction": {
        "interaction_id",
        "topic",
        "follow_up_action",
        "follow_up_date",
        "follow_up_status",
        "notes"
    },
    "get_pending_followups": {"target_date"},
    "get_hcp_interaction_history": {"hcp_id"}
}

# ---------------- SYSTEM INSTRUCTION ---------------- #

SYSTEM_INSTRUCTION = """
You are an AI CRM assistant for managing doctor (HCP) interactions.

Your job:
- Understand user intent and map it to available tools use cases
- Select correct tool(s)
- Extract required and optional mentioned inputs for tools
- Return execution steps in JSON

----------------------
AVAILABLE TOOLS
----------------------

1. search_hcp

Required Inputs:
- NONE

Optional Inputs:
- name (string)
- hospital (string)
- hcp_id (int)

Output:
List of doctor(s) with:
- hcp_id
- name
- hospital
- specialization
- city

Use cases:
- Find a doctor existence or details based on name or hospital
- Get HCP ID for other tools that need it
- No details then this tool return recent doctors added to database with their details


2. log_interaction

Required Inputs:
- name (string)
- hospital (string)
- topic (string)

Optional Inputs:
- notes (string)
- city (string)
- specialization (string)
- follow_up_action (string)
- follow_up_date (YYYY-MM-DD)

Output:
- message (string) - success message
- interaction_id
- hcp_id
- hcp_created (boolean) - whether a new HCP was created or existing one was used

Use cases:
- Log interaction(Add to databse) using detail that user provide about doctor and interaction
- This tool can log interaction irrespective of existence of doctor in database, so no extra checks required.

3. edit_interaction

Required Inputs:
- interaction_id (int)

Optional Inputs:
- notes (string)
- follow_up_action (string)
- follow_up_status (pending/completed/cancelled/no_follow_up)
- follow_up_date (YYYY-MM-DD)

OUTPUT:
- message (string) - success message
- interaction_id
- updated_fields (list of fields that were updated with this tool call)

Use cases:
- Update interaction details like notes, follow-up action, status or date.
- Sometimes interaction_id can be obtained from get_hcp_interaction_history tool calls only if interaction_id not mentioned in user input.


4. get_pending_followups

Required Inputs:
- NONE

Optional Inputs:
- target_date (YYYY-MM-DD)

OUTPUT:
List of pending follow-ups with:
- interaction_id
- hcp_id
- name
- hospital
- follow_up_action
- follow_up_date
- topic

Use cases:
- If date provided, get all pending follow-ups that are due on or before the target date. 
- If no date provided, get all pending follow-ups irrespective of date.

5. get_hcp_interaction_history

Required Inputs:
- hcp_id (int)

Optional Inputs:
- NONE

OUTPUT:
- List of interactions with:
    - interaction_id
    - topic
    - interaction_date
    - follow_up_action
    - follow_up_date
    - follow_up_status
    - notes

Use cases:
- Get details of interactions(and interaction history) with any doctor.
- This tool can be used for getting interaction_id


IMPORTANT:
Extract structured data from user sentence. Keep data type format as provided in instructions above.

----------------------
RULES
----------------------

- ALWAYS return ONLY valid JSON
- NO explanation text
- NO extra text outside JSON
- NO extra tool calls
- Use correct tool name EXACTLY
- All dates passed to tools must be in YYYY-MM-DD format.
- If required input missing → first get it using another tool
- If hcp_id required for another tool:
  → first call search_hcp
  → then use $prev.hcp_id
  → $prev to be used for only for missing fields, that are not present in user input

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
        plan = Plan(**json.loads(content))
    except Exception as e:
        return {"output": f"Invalid LLM response {str(e)}"}

    return {
        "plan": plan.dict(),
        "input": user_input
    }

def normalize_dates(data):

    if "follow_up_date" in data:

        value = str(data["follow_up_date"]).lower()

        match = re.search(r"(\\d+)\\s*day", value)

        if match:
            days = int(match.group(1))

            data["follow_up_date"] = (
                date.today() + timedelta(days=days)
            ).isoformat()

    return data

# ---------------- EXECUTE STEP ---------------- #

def execute_plan(state: AgentState):
    plan = state.get("plan")
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

            if isinstance(v, str) and v.startswith("$prev"):

                if (
                    v.startswith("$prev[0].")
                    and isinstance(prev_result, list)
                    and len(prev_result) > 0
                    and isinstance(prev_result[0], dict)
                ):

                    key = v.split(".", 1)[1]
                    data[k] = prev_result[0].get(key)

                elif (
                    v.startswith("$prev.")
                    and isinstance(prev_result, dict)
                ):

                    key = v.split(".", 1)[1]
                    data[k] = prev_result.get(key)

        allowed = ALLOWED_PARAMS.get(tool_name, set())

        data = {
            k: v for k, v in data.items()
            if k in allowed
        }

        data = normalize_dates(data)

        try:
            result = tool.invoke(data)
            if result is None:
                raise Exception(f"{tool_name} returned None")

            if isinstance(result, dict):

                if result.get("success") is False:
                    raise Exception(result.get("error"))

            if isinstance(result, list) and len(result) == 0:
                raise Exception(f"{tool_name} returned empty result")
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

                data_result = result.get("data")

                if isinstance(data_result, list) and len(data_result) > 0:
                    prev_result = data_result[0]

                elif isinstance(data_result, dict):
                    prev_result = data_result

                else:
                    prev_result = data_result

    return {"output": last_result}

def execute_with_retry(state: AgentState, max_retries=2):
    user_input = state["input"]
    plan = state.get("plan", {})

    logger.info(f"[INPUT] {user_input}")

    for attempt in range(max_retries + 1):
        logger.info(f"[RETRY {attempt + 1}]")
        logger.info(f"[PLAN] {json.dumps(plan)}")

        print(f"Retry attempt {attempt+1}")
        print("Executing plan:", json.dumps(plan, indent=2))

        result = execute_plan({
            "plan": plan,
            "input": user_input
        })

        # SUCCESS
        if not result.get("error"):
            raw_output = result["output"]
            logger.info(f"[RAW OUTPUT] {raw_output}")

            formatted_response = generate_response(
                user_input=user_input,
                raw_result=raw_output
            )
            logger.info(f"[FINAL RESPONSE] {formatted_response}")

            return {
                "raw_output": raw_output,
                "output": formatted_response
            }

        # FAILURE
        error_info = result
        logger.error(
            f"[FAILED]"
            f"Attempt={attempt+1} Failed | "
            f"Tool={error_info.get('failed_tool')} | "
            f"Error={error_info['message']}"
        )

        print(f"\n--- RETRY {attempt+1} ---")
        print("Error:", error_info["message"])

        # stop if max retries reached
        if attempt == max_retries:
            logger.error(
                f"Execution Failed After Retries | "
                f"Last Error={error_info['message']}"
            )

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

Previous plan:
{json.dumps(plan)}

Failed tool:
{error_info.get('failed_tool')}

Failed step index:
{error_info.get('step')}

Fix the plan.

Rules:
- Understand the error and fix the plan accordingly
- Ensure required inputs are present and fetched correctly from user input
- Make sure no unnecessary tools called and remove them from plan
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
            logger.info(
                f"Retry Plan Generated: {json.dumps(plan)}"
            )
        except Exception as e:
            logger.error(
                f"Retry Plan Parsing Failed: {str(e)}"
            )
            
            return {"output": "Failed to fix plan got error: " + str(e)}

    return {"output": "Execution failed"}

# ------------Response generation function------------
def generate_response(user_input, raw_result):

    prompt = f"""
You are an AI CRM assistant.

User request:
{user_input}

Raw tool output:
{json.dumps(raw_result, indent=2)}

Instructions:
- Answer ONLY what the user asked.
- Do not expose unnecessary information.
- Be concise and professional.
- If the user asks for a single field, return only that field.
- If the operation succeeded, confirm it naturally.
- Answer ONLY based on provided text
- If no data is available, clearly state that.
"""

    response = llm.invoke([
        SystemMessage(content=prompt)
    ])

    return response.content

# ---------------- GRAPH ---------------- #

builder = StateGraph(AgentState)

builder.add_node("plan", create_plan)
builder.add_node("execute", execute_with_retry)

builder.set_entry_point("plan")
builder.add_edge("plan", "execute")
builder.set_finish_point("execute")

graph = builder.compile()