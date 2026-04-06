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
    api_key=os.getenv("GROQ_API_KEY")
)

class AgentState(dict):
    pass

import json

def decide_action(state: AgentState):
    user_input = state["input"]

    prompt = f"""
You are an AI CRM assistant.

Your job:
1. Understand the user request
2. Decide which tool(s) to use
3. Extract ALL required data
4. If required data is missing → ask user

---

Available tools:

1. search_hcp
Description: Find doctor details
Input:
- hcp_id (optional)
- name (optional)
- hospital (optional)

---

2. log_interaction
Description: Log a new interaction with doctor
Required:
- doctor_name (string)
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
Description: Fetch follow-ups
Optional:
- target_date (YYYY-MM-DD)

---

5. get_hcp_interaction_history
Description: Get interaction history
Required:
- hcp_id (int)

---

RULES:
- Output ONLY valid JSON
- No explanations, no markdown
- Always follow schema strictly

---

If required information is missing:

Return:
{{
  "action": "ask_user",
  "question": "Ask clearly for missing required information"
}}

---

If all data is available:

Return:
{{
  "steps": [
    {{
      "tool": "tool_name",
      "data": {{...}}
    }}
  ]
}}

---

For multi-step tasks:
- First find HCP Id using search_hcp
- Then use "$prev.hcp_id" in next step

---

User input:
{user_input}
"""

    response = llm.invoke(prompt)

    content = response.content.strip()

    try:
        parsed = json.loads(content)

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
            "error": "INVALID_JSON_FROM_LLM",
            "raw_output": content,
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
        