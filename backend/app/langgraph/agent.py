import os
import json
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph

load_dotenv()

from tools import (
    search_hcp_tool,
    log_interaction_tool,
    edit_interaction_tool,
    get_pending_followups_tool,
    get_hcp_interaction_history_tool
)

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.2
)

def call_llm_with_retry(prompt, max_retries=3):
    for attempt in range(max_retries):

        response = llm.invoke(prompt)
        content = response.content.strip()

        try:
            parsed = json.loads(content)
            return parsed

        except json.JSONDecodeError:
            print(f"Retry {attempt+1}: Invalid JSON")

    return {
        "action": "ask_user",
        "question": "Sorry, I didn't understand. Can you rephrase?"
    }

def validate_plan(parsed):

    if "steps" not in parsed and parsed.get("action") != "ask_user":
        return False

    if "steps" in parsed:
        for step in parsed["steps"]:
            if "tool" not in step or "data" not in step:
                return False

    return True

class AgentState(dict):
    pass

def decide_action(state: AgentState):
    user_input = state["input"]

    prompt = """
You are an AI CRM assistant.

Your job:
1. Understand the user request
2. Decide which tool(s) to use
3. Extract ALL required data
4. If required data is missing → ask user

---

Available tools:

1. search_hcp
Description: Find doctor details by ID or name + hospital. 
This can be used as a pre-tool call for other tasks when hcp_id is not provided but name and hospital are available.
Input:
- hcp_id (optional)
- name (optional)
- hospital (optional)

---

2. log_interaction
Description: Log a new interaction with doctor
Required:
- name (string)
- hospital (string)

Optional:
- specialization
- city
- interaction_date (YYYY-MM-DD)
- topic
- follow_up_action
- follow_up_date (YYYY-MM-DD)
- notes

---

3. edit_interaction
Description: Update an interaction
Required:
- interaction_id (int)

Optional:
- topic
- follow_up_action
- follow_up_date (YYYY-MM-DD)
- follow_up_status (pending/completed/cancelled/no_follow_up)
- notes

---

4. get_pending_followups
Description: Fetch follow-ups that are pending
Optional:
- target_date (YYYY-MM-DD)

---

5. get_hcp_interaction_history
Description: Get interaction history
Required:
- hcp_id (int)

---

RULES:

1. NEVER ask user for HCP ID if doctor name or hospital is provided.
   → ALWAYS use search_hcp first.

2. Prefer multi-step reasoning over asking user.

3. Only ask user if:
   - interaction_id is missing for edit
   - doctor_name AND hospital BOTH missing
   - data cannot be inferred using any tool

4. When doctor name is given:
   → ALWAYS first call search_hcp
   → THEN use "$prev.hcp_id" for next step

5. Always minimize user interaction.

---

Examples:

User: "Show history of Dr Sharma"
Output:
{
  "steps": [
    {
      "tool": "search_hcp",
      "data": {"name": "Sharma"}
    },
    {
      "tool": "get_hcp_interaction_history",
      "data": {"hcp_id": "$prev.hcp_id"}
    }
  ]
}

---

User: "Show followups"
Output:
{
  "steps": [
    {
      "tool": "get_pending_followups",
      "data": {"field_name": "value"}
    }
  ]
}

---

User: "Update interaction"
Output:
{
  "action": "ask_user",
  "question": "Please provide interaction_id"
}

---
User input:
"""

    prompt += user_input

    try:
        parsed = call_llm_with_retry(prompt)

        # Validate structure
        if not validate_plan(parsed):
            return {
                "ask_user": True,
                "question": "Can you clarify your request?",
                "input": user_input
            }

        # Case 1 → ask user
        if parsed.get("action") == "ask_user":
            return {
                "ask_user": True,
                "question": parsed.get("question"),
                "input": user_input
            }

        # Case 2 → valid plan
        return {
            "plan": parsed.get("steps", []),
            "input": user_input
        }

    except Exception as e:
        return {
            "ask_user": True,
            "question": f"Something went wrong got error: {e}. Can you rephrase?",
            "input": user_input
        }
    
def execute_plan(state):
    steps = state["plan"]
    prev_result = {}


    TOOL_MAP = {
        "search_hcp": search_hcp_tool,
        "log_interaction": log_interaction_tool,
        "edit_interaction": edit_interaction_tool,
        "get_pending_followups": get_pending_followups_tool,
        "get_hcp_interaction_history": get_hcp_interaction_history_tool
    }

    for step in steps:
        tool_name = step["tool"]
        data = step.get("data", {})

        for key, value in data.items():
            if isinstance(value, str) and value.startswith("$prev"):
                field = value.split(".")[-1]
                data[key] = prev_result.get(field)

        tool = TOOL_MAP.get(tool_name)

        if not tool:
            return {"error": f"UNKNOWN_TOOL_{tool_name}"}
        
        if tool_name == "edit_interaction":
            result = tool(data["interaction_id"], data)
        elif tool_name == "get_hcp_interaction_history":
            result = tool(data["hcp_id"])
        else:
            result = tool(**data) if isinstance(data, dict) else tool(data)

        if isinstance(result, list) and len(result) > 0:
            prev_result = result[0]
        elif isinstance(result, dict):
            prev_result = result
        else:
            prev_result = {}

    return {"result": result}

def route_after_decision(state):
    if state.get("ask_user"):
        return "ask_user"
    elif state.get("plan"):
        return "execute"
    else:
        return "error"
    
def ask_user_node(state):
    return {
        "result": state.get("question", "Need more information from user.")
    }

def error_node(state):
    return {
        "result": "Something went wrong. Please try again."
    }

builder = StateGraph(dict)

builder.add_node("decide", decide_action)
builder.add_node("execute", execute_plan)
builder.add_node("ask_user", ask_user_node)
builder.add_node("error", error_node)

builder.set_entry_point("decide")

builder.add_conditional_edges(
    "decide",
    route_after_decision,
    {
        "execute": "execute",
        "ask_user": "ask_user",
        "error": "error"
    }
)

builder.set_finish_point("execute")
builder.set_finish_point("ask_user")
builder.set_finish_point("error")

graph = builder.compile()

if __name__ == "__main__":
    while True:
        user_input = input("\nEnter your query: ")

        result = graph.invoke({"input": user_input})

        print("\nResponse:\n", result.get("result", "No result"))
        