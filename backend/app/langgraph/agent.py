import json
from dotenv import load_dotenv
import os
from typing import TypedDict

from langgraph.graph import StateGraph
from langchain_groq import ChatGroq

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
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.2
)

# ---------------- STATE ---------------- #

class AgentState(TypedDict):
    input: str
    extracted: dict
    plan: list
    ask_user: bool
    question: str
    output: str

# ---------------- RETRY ---------------- #

def call_llm_with_retry(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = llm.invoke(prompt)
            content = response.content.strip()

            print("\n--- RAW ---")
            print(content)

            # 🔥 extract only JSON part
            start = content.find("{")
            end = content.rfind("}") + 1

            if start != -1 and end != -1:
                content = content[start:end]

            return json.loads(content)

        except Exception as e:
            print(f"Retry {attempt+1}: {e}")

    return {"action": "ask_user", "question": "Can you rephrase?"}

# ---------------- VALIDATION ---------------- #

def validate_plan(parsed):
    if "steps" not in parsed and parsed.get("action") != "ask_user":
        return False
    if "steps" in parsed:
        for step in parsed["steps"]:
            if "tool" not in step or "data" not in step:
                return False
    return True

# ---------------- STEP 1: EXTRACT ---------------- #

def extract_intent(state: AgentState):
    user_input = state["input"]

    prompt = f"""
Return ONLY valid JSON.

No explanation. No text.

{{
  "intent": "search|history|log|edit|followup",
  "name": "string or null",
  "hospital": "string or null",
  "interaction_id": null
}}

User input:
{user_input}
"""

    parsed = call_llm_with_retry(prompt)

    return {
        "extracted": parsed,
        "input": user_input
    }

# ---------------- STEP 2: PLAN ---------------- #

def plan_action(state: AgentState):
    extracted = state["extracted"]

    prompt = f"""
You MUST return ONLY valid JSON.

Data:
{json.dumps(extracted)}

Rules:
- If name exists → ALWAYS call search_hcp first
- Then use "$prev.hcp_id"
- Then call get_hcp_interaction_history if intent = history
- NEVER ask for HCP ID if name exists

Return:
{{
  "steps": [
    {{
      "tool": "...",
      "data": {{...}}
    }}
  ]
}}
"""

    parsed = call_llm_with_retry(prompt)

    if not validate_plan(parsed):
        return {
            "ask_user": True,
            "question": "Can you clarify?",
            "input": state["input"]
        }

    return {
        "plan": parsed.get("steps", []),
        "input": state["input"]
    }

# ---------------- STEP 3: EXECUTE ---------------- #

def execute_plan(state: AgentState):
    plan = state["plan"]

    tools_map = {
        "search_hcp": search_hcp_tool,
        "log_interaction": log_interaction_tool,
        "edit_interaction": edit_interaction_tool,
        "get_pending_followups": get_pending_followups_tool,
        "get_hcp_interaction_history": get_hcp_interaction_history_tool
    }

    prev_result = {}

    for step in plan:
        tool_name = step["tool"]
        data = step["data"]

        # FIX doctor_name → name mismatch
        if "doctor_name" in data:
            data["name"] = data.pop("doctor_name")

        for k, v in data.items():
            if isinstance(v, str) and "$prev." in v:
                key = v.split(".")[1]
                data[k] = prev_result.get(key)

    for step in plan:
        tool_name = step["tool"]
        data = step["data"]

        # replace $prev
        for k, v in data.items():
            if isinstance(v, str) and "$prev." in v:
                key = v.split(".")[1]
                data[k] = prev_result.get(key)

        tool = tools_map.get(tool_name)

        if not tool:
            return {"output": f"Unknown tool: {tool_name}"}

        result = tool(**data)

        if isinstance(result, list) and len(result) > 0:
            prev_result = result[0]
        elif isinstance(result, dict):
            prev_result = result

    return {"output": result}

# ---------------- ROUTER ---------------- #

def route_after_plan(state):
    if state.get("ask_user"):
        return "ask_user"
    elif state.get("plan"):
        return "execute"
    else:
        return "error"

# ---------------- ASK USER ---------------- #

def ask_user_node(state):
    return {"output": state.get("question", "Need more info")}

# ---------------- ERROR ---------------- #

def error_node(state):
    return {"output": "Something went wrong"}

# ---------------- GRAPH ---------------- #

builder = StateGraph(AgentState)

builder.add_node("extract", extract_intent)
builder.add_node("plan", plan_action)
builder.add_node("execute", execute_plan)
builder.add_node("ask_user", ask_user_node)
builder.add_node("error", error_node)

builder.set_entry_point("extract")

builder.add_edge("extract", "plan")

builder.add_conditional_edges(
    "plan",
    route_after_plan,
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

# ---------------- RUN ---------------- #

if __name__ == "__main__":
    while True:
        user_input = input("\nEnter your query: ")

        result = graph.invoke({"input": user_input})

        print("\nResponse:\n", result["output"])