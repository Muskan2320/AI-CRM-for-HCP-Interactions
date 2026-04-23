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
    temperature=0
)

# ---------------- STATE ---------------- #

class AgentState(TypedDict):
    input: str
    plan: dict
    output: str

# ---------------- SYSTEM PROMPT ---------------- #

SYSTEM_PROMPT = """
You are an AI CRM assistant.

Available tools:
- search_hcp(name?, hospital?, hcp_id?)
- log_interaction(name, hospital, notes?)
- edit_interaction(interaction_id, ...)
- get_pending_followups()
- get_hcp_interaction_history(hcp_id)

Rules:
- Return ONLY JSON
- No explanation
- If multiple steps needed, return in order

Format:
{
  "steps": [
    {
      "tool": "tool_name",
      "data": {}
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

# ---------------- STEP 1: PLAN ---------------- #

def create_plan(state: AgentState):
    user_input = state["input"]

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_input)
    ]

    response = llm.invoke(messages)
    content = response.content.strip()

    print("\n--- RAW LLM ---")
    print(content)

    # extract JSON safely
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

# ---------------- STEP 2: EXECUTE ---------------- #

def execute_plan(state: AgentState):
    plan = state.get("plan", {})
    steps = plan.get("steps", [])

    prev_result = None

    for step in steps:
        tool_name = step.get("tool")
        data = step.get("data", {})

        tool = TOOLS.get(tool_name)

        if not tool:
            return {"output": f"Unknown tool: {tool_name}"}

        # handle chaining
        for k, v in data.items():
            if isinstance(v, str) and "$prev." in v and prev_result:
                key = v.split(".")[1]
                data[k] = prev_result.get(key)

        result = tool(**data)

        if isinstance(result, list) and len(result) > 0:
            prev_result = result[0]
        elif isinstance(result, dict):
            prev_result = result

    return {"output": result}

# ---------------- GRAPH ---------------- #

builder = StateGraph(AgentState)

builder.add_node("plan", create_plan)
builder.add_node("execute", execute_plan)

builder.set_entry_point("plan")
builder.add_edge("plan", "execute")

builder.set_finish_point("execute")

graph = builder.compile()