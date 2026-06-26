import requests
import json
import os
from dotenv import load_dotenv

BASE_URL = "http://127.0.0.1:8000"

load_dotenv()

EMAIL = os.getenv("TEST_EMAIL")
PASSWORD = os.getenv("TEST_PASSWORD")


def get_token():
    response = requests.post(
        f"{BASE_URL}/login",
        json={
            "email": EMAIL,
            "password": PASSWORD
        }
    )

    response.raise_for_status()

    return response.json()["access_token"]


TOKEN = get_token()


headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}


TEST_PROMPTS = [

    # Search tests
    "Show doctor Himani from Apollo Hospital",

    # Interaction logging
    "Log interaction with Dr Himani from Apollo Hospital regarding diabetes awareness",

    # Multi-step chaining
    "Find Dr Shankar from Apollo Hospital and show his interaction history",

    # Followups
    "Show pending followups",

    # Complex orchestration
    "Find pending followups and mark the earliest one as completed",

    # Edit interaction
    "Mark interaction 5 as completed",

    # Retry/failure
    "Show history of doctor that does not exist",

    # Date normalization
    "Log interaction with Dr Raj from Fortis Hospital and schedule followup after 5 days",

    "What is HCP id doctor sharma",

    "Last interaction happened with which doctor",

    "I want to get the interaction with interaction id 8"
]


passed = 0
failed = 0


def run_test(prompt):
    global passed, failed

    print("\n" + "=" * 80)

    print("TEST PROMPT:")
    print(prompt)

    try:

        response = requests.post(
            f"{BASE_URL}/chat",
            headers=headers,
            json={
                "message": prompt
            }
        )

        print("\nSTATUS CODE:")
        print(response.status_code)

        print("\nRESPONSE:")
        print(json.dumps(response.json(), indent=2))

        if response.status_code == 200:
            passed += 1
        else:
            failed += 1

    except Exception as e:

        failed += 1

        print("\nERROR:")
        print(str(e))


if __name__ == "__main__":

    for prompt in TEST_PROMPTS:
        run_test(prompt)

    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests : {len(TEST_PROMPTS)}")
    print(f"Passed      : {passed}")
    print(f"Failed      : {failed}")
    print("=" * 80)