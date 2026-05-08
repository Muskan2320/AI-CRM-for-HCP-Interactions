import requests

from langchain.tools import tool

BASE_URL = "http://127.0.0.1:8000"


@tool
def search_hcp_tool(
    hcp_id: int = None,
    name: str = None,
    hospital: str = None
):
    """
    Search HCP using hcp_id OR name and hospital.
    """

    params = {}

    if hcp_id:
        params["hcp_id"] = hcp_id
    else:
        if name:
            params["name"] = name

        if hospital:
            params["hospital"] = hospital

    response = requests.get(
        f"{BASE_URL}/hcp/search",
        params=params
    )

    return response.json()


@tool
def log_interaction_tool(
    name: str,
    hospital: str,
    topic: str,
    specialization: str = None,
    city: str = None,
    interaction_date: str = None,
    follow_up_action: str = None,
    follow_up_date: str = None,
    notes: str = None
):
    """
    Log interaction with doctor.
    """

    payload = {
        "name": name,
        "hospital": hospital,
        "topic": topic,
        "specialization": specialization,
        "city": city,
        "interaction_date": interaction_date,
        "follow_up_action": follow_up_action,
        "follow_up_date": follow_up_date,
        "notes": notes
    }

    payload = {
        k: v for k, v in payload.items()
        if v is not None
    }

    print("\n--- Logging Interaction with Data ---")
    print(payload)

    response = requests.post(
        f"{BASE_URL}/log-interaction",
        json=payload
    )

    return response.json()


@tool
def edit_interaction_tool(
    interaction_id: int,
    topic: str = None,
    follow_up_action: str = None,
    follow_up_date: str = None,
    follow_up_status: str = None,
    notes: str = None
):
    """
    Edit interaction details.
    """

    payload = {
        "topic": topic,
        "follow_up_action": follow_up_action,
        "follow_up_date": follow_up_date,
        "follow_up_status": follow_up_status,
        "notes": notes
    }

    payload = {
        k: v for k, v in payload.items()
        if v is not None
    }

    response = requests.put(
        f"{BASE_URL}/interaction/{interaction_id}",
        json=payload
    )

    return response.json()


@tool
def get_pending_followups_tool(target_date: str = None):
    """
    Get pending followups.
    """

    params = {}

    if target_date:
        params["target_date"] = target_date

    response = requests.get(
        f"{BASE_URL}/pending-follow-ups",
        params=params
    )

    return response.json()


@tool
def get_hcp_interaction_history_tool(hcp_id: int):
    """
    Get HCP interaction history.
    """

    response = requests.get(
        f"{BASE_URL}/hcp/{hcp_id}/interaction-history"
    )

    return response.json()


if __name__ == "__main__":
    print(get_pending_followups_tool.invoke({}))