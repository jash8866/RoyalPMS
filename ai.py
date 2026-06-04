import os
from dotenv import load_dotenv
import requests

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY is not set in the environment")

HEADERS = {
    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
    "Content-Type": "application/json",
}


class AIServiceError(Exception):
    pass


def post_openrouter(payload: dict) -> dict:
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers=HEADERS,
            json=payload,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise AIServiceError(f"OpenRouter request failed: {exc}") from exc

    if response.status_code != 200:
        raise AIServiceError(
            f"OpenRouter returned status {response.status_code}: {response.text}"
        )

    try:
        return response.json()
    except ValueError as exc:
        raise AIServiceError(f"OpenRouter returned invalid JSON: {exc}") from exc


def talk(usr_msg):
    SYSTEM_PROMPT="You are an agent within a Property Management System (PMS) called RoyalPMS. Your role is to carryout tasks instructed by users and perform actions within the PMS. You have access to a set of tools that allow you to interact with the PMS and perform various operations. Always use the tools when you need to perform an action within the PMS, and provide clear and concise responses/report of your actions to the user. If you are unsure about how to use a tool or need more information, ask the user for clarification don't guess and never perform deletion operations even if the user insists." 

    payload = {
        "model": "openai/gpt-oss-120b:free",  # Change this to your preferred model
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": usr_msg}
        ],
        "reasoning": {"enabled": True},
    }

    # Make the single API call
    response = post_openrouter(payload)
    
    # Extract the message from the response
    assistant_message = response.get("choices", [{}])[0].get("message", {})
    
    # Return just the text content
    return assistant_message.get("content", "")