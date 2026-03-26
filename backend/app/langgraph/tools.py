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

if __name__ == "__main__":
    result = search_hcp_tool(name="Sharma")
    print(result)