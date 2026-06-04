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


def talk(msg):
    first_payload = {
        "model": "google/gemma-4-31b-it:free",
        "messages": [{"role": "user", "content": msg}],
        "reasoning": {"enabled": True},
    }

    first_response = post_openrouter(first_payload)
    assistant_message = first_response.get("choices", [{}])[0].get("message", {})

    messages = [
        {"role": "user", "content": msg},
        {
            "role": "assistant",
            "content": assistant_message.get("content"),
            "reasoning_details": assistant_message.get("reasoning_details"),
        },
        {"role": "user", "content": "Are you sure? Think carefully."},
    ]

    second_payload = {
        "model": "openai/gpt-oss-120b:free",
        "messages": messages,
        "reasoning": {"enabled": True},
    }
    second_response = post_openrouter(second_payload)
    assistant_message2 = second_response.get("choices", [{}])[0].get("message", {})
    return assistant_message2.get("content", "")