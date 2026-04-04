import os
import json
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph

load_dotenv()

from app.langgraph.tools import (
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
- First find HCP using search_hcp
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