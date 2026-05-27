import requests
import json

BASE_URL = "http://127.0.0.1:8000"


TOKEN = "PASTE_YOUR_JWT_TOKEN_HERE"


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
    "Log interaction with Dr Raj from Fortis Hospital and schedule followup after 5 days"
]


def run_test(prompt):

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

    except Exception as e:

        print("\nERROR:")
        print(str(e))


if __name__ == "__main__":

    for prompt in TEST_PROMPTS:
        run_test(prompt)