import os
import json
from dotenv import load_dotenv
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
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.3-70b-versatile",
    temperature=0
)

# ---------------- STATE ---------------- #

class AgentState(TypedDict, total=False):
    input: str
    extracted: dict
    plan: list
    ask_user: bool
    question: str
    output: str

# ---------------- HELPERS ---------------- #

def normalize_extracted_data(data: dict, user_input: str):
    text = user_input.lower()

    # ---- DETECT LOG INTERACTION ----
    if any(word in text for word in ["interaction", "met", "spoke", "discussed"]):
        data["intent"] = "log"

    # ---- DETECT COUNT ----
    if "how many" in text or "count" in text:
        data["intent"] = "count"

    # ---- GENERIC NAME FIX ----
    invalid_names = ["doctor", "doctors", "all", "any"]

    name = data.get("name")
    if name and name.lower().strip() in invalid_names:
        data["name"] = None
        if data.get("intent") != "count":
            data["intent"] = "list"

    return data

# ---------------- RETRY ---------------- #

def call_llm_with_retry(prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = llm.invoke(prompt)
            content = response.content.strip()

            print("\n--- RAW ---")
            print(content)

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
    if parsed.get("action") == "ask_user":
        return True

    if "steps" not in parsed:
        return False

    for step in parsed["steps"]:
        if "tool" not in step or "data" not in step:
            return False

    return True

# ---------------- STEP 1: EXTRACT ---------------- #

def extract_intent(state: AgentState):
    user_input = state["input"]

    prompt = f"""
Return ONLY valid JSON.

{{
  "intent": "search|history|log|edit|followup|list|count",
  "name": "string or null",
  "hospital": "string or null",
  "interaction_id": null
}}

User input:
{user_input}
"""

    parsed = call_llm_with_retry(prompt)

    parsed = normalize_extracted_data(parsed, user_input)

    return {
        "extracted": parsed,
        "input": user_input
    }

# ---------------- STEP 2: PLAN ---------------- #

def plan_action(state: AgentState):
    extracted = state["extracted"]

    intent = extracted.get("intent")
    name = extracted.get("name")
    hospital = extracted.get("hospital")

    # LIST
    if intent == "list":
        return {
            "plan": [
                {
                    "tool": "search_hcp",
                    "data": {
                        "hospital": hospital
                    }
                }
            ],
            "input": state["input"]
        }

    # COUNT
    if intent == "count":
        return {
            "plan": [
                {
                    "tool": "search_hcp",
                    "data": {
                        "hospital": hospital
                    }
                },
                {
                    "tool": "count_results",
                    "data": {
                        "items": "$prev"
                    }
                }
            ],
            "input": state["input"]
        }

    # HISTORY
    if intent == "history" and name:
        return {
            "plan": [
                {
                    "tool": "search_hcp",
                    "data": {
                        "name": name,
                        "hospital": hospital
                    }
                },
                {
                    "tool": "get_hcp_interaction_history",
                    "data": {
                        "hcp_id": "$prev.hcp_id"
                    }
                }
            ],
            "input": state["input"]
        }

    # fallback LLM (restricted tools)
    prompt = f"""
Return ONLY valid JSON.

Allowed tools:
search_hcp, log_interaction, edit_interaction,
get_pending_followups, get_hcp_interaction_history

Data:
{json.dumps(extracted)}

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

# ---------------- TOOL: COUNT ---------------- #

def count_results(items):
    if isinstance(items, list):
        return {"count": len(items)}
    return {"count": 0}

# ---------------- STEP 3: EXECUTE ---------------- #

def execute_plan(state: AgentState):
    plan = state["plan"]

    tools_map = {
        "search_hcp": search_hcp_tool,
        "log_interaction": log_interaction_tool,
        "edit_interaction": edit_interaction_tool,
        "get_pending_followups": get_pending_followups_tool,
        "get_hcp_interaction_history": get_hcp_interaction_history_tool,
        "count_results": count_results
    }

    prev_result = {}

    for step in plan:
        tool_name = step["tool"]
        data = step["data"]

        # fix doctor_name → name
        if "doctor_name" in data:
            data["name"] = data.pop("doctor_name")

        # normalize name
        if "name" in data and data["name"]:
            data["name"] = data["name"].lower().replace("dr ", "").strip()

        # handle $prev
        for k, v in data.items():
            if isinstance(v, str) and v == "$prev":
                data[k] = prev_result

            elif isinstance(v, str) and "$prev." in v:
                key = v.split(".")[1]
                value = prev_result.get(key)

                if value is None:
                    return {
                        "output": f"Could not find {key}. Please refine your query."
                    }

                data[k] = value

        tool = tools_map.get(tool_name)

        if not tool:
            return {"output": f"Unknown tool: {tool_name}"}

        result = tool(**data)

        # handle result
        if isinstance(result, list):
            if len(result) == 0:
                return {"output": "No matching doctor found."}
            prev_result = result

        elif isinstance(result, dict):
            prev_result = result

        else:
            prev_result = {}

    return {"output": result}

# ---------------- ROUTING ---------------- #

def route_after_plan(state):
    if state.get("ask_user"):
        return "ask_user"
    elif state.get("plan"):
        return "execute"
    else:
        return "error"

def ask_user_node(state):
    return {"output": state.get("question", "Need more information")}

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
        print("\nResponse:\n", result.get("output"))