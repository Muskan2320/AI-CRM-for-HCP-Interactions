import requests

BASE_URL = "http://127.0.0.1:8000"

def search_hcp_tool(name: str = None, hospital: str = None):
    params = {}

    if name:
        params["name"] = name

    if hospital:
        params["hospital"] = hospital

    response = requests.get(f"{BASE_URL}/hcp/search", params=params)

    return response.json()

def log_interaction_tool(data: dict):
    response = requests.post(f"{BASE_URL}/log-interaction", json=data)

    return response.json()

def edit_interaction_tool(interaction_id: int, data: dict):
    response = requests.put(
        f"{BASE_URL}/interaction/{interaction_id}",
        json = data
    )

    return response.json()

if __name__ == "__main__":
    # result = search_hcp_tool(name="Sharma")
    # print(result)

    # sample_data = {
    #     "doctor_name": "Dr Test",
    #     "hospital": "Apollo",
    #     "specialization": "Cardiology",
    #     "city": "Delhi",
    #     "interaction_date": "2026-03-20",
    #     "topic": "Diabetes drug",
    #     "follow_up_action": "Send samples",
    #     "follow_up_date": "2026-03-25",
    #     "notes": "Doctor interested"
    # }

    # result = log_interaction_tool(sample_data)
    # print(result)

    result = edit_interaction_tool(
        interaction_id=7,
        data={
            "follow_up_status": "completed",
            "notes": "Follow-up done successfully"
        }
    )
    print(result)