from multiprocessing.dummy import connection
import os
import json
import requests
from dbcon import *



# =====================================================
# CONFIG
# =====================================================

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

MODEL = "openai/gpt-oss-120b:free"

SYSTEM_PROMPT = """
You are an agent within a Property Management System (PMS)
called RoyalPMS.

Your role is to carry out tasks instructed by users and
perform actions within the PMS.

Rules:
- Always use tools when PMS data is required.
- Never invent PMS data.
- Ask for clarification when needed.
- Never perform deletion operations.
- Report actions performed.
-conversations should be strictly regarding the PMS only and should not deviate to other topics.
"""


# =====================================================
#  DATABASE
# =====================================================
db = DatabaseConnection(host="localhost", username="root", password="", db_name="royalpms_cryst8000")
db.connect()
reservations = db.fetch_reservations()
print("Reservations loaded from DB:")
for res in reservations:
    print(res)


# =====================================================
# TOOLS EXPOSED TO AI
# =====================================================

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_reservations",
            "description": "Search reservations by guest name",
            "parameters": {
                "type": "object",
                "properties": {
                    "guest_name": {
                        "type": "string"
                    }
                },
                "required": ["guest_name"]
            }
        }
    }
]


# =====================================================
# REAL TOOL IMPLEMENTATIONS
# =====================================================

def search_reservations(guest_name):

    matches = []

    for reservation in reservations:

        if guest_name.lower() in reservation["guest_name"].lower():
            matches.append(reservation)

        return {
            "success": True,

            "matches": matches,

            # frontend will consume this
            "ui_actions": [
                {
                    "type": "navigate",
                    "page": "reservations"
                },
                {
                    "type": "filter_reservations",
                    "guest_name": guest_name
                }
            ]
        }


available_tools = {
    "search_reservations": search_reservations
}


# =====================================================
# CHAT MEMORY
# =====================================================

messages = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT
    }
]


# =====================================================
# OPENROUTER CALL
# =====================================================

def call_model():

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization":
                f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type":
                "application/json"
        },
        json={
            "model": MODEL,
            "messages": messages,
            "tools": tools,
            "reasoning": {
                "enabled": True
            }
        }
    )

    response.raise_for_status()

    return response.json()


# =====================================================
# TOOL LOOP
# =====================================================

def process_ai():

    while True:

        response = call_model()

        assistant_message = (
            response["choices"][0]["message"]
        )

        messages.append({
            "role":
                "assistant",

            "content":
                assistant_message.get("content"),

            "tool_calls":
                assistant_message.get("tool_calls"),

            "reasoning_details":
                assistant_message.get(
                    "reasoning_details"
                )
        })

        tool_calls = assistant_message.get(
            "tool_calls"
        )

        if not tool_calls:

            print(
                "\nAssistant:",
                assistant_message.get("content")
            )

            return

        for tool_call in tool_calls:

            tool_name = (
                tool_call["function"]["name"]
            )

            args = json.loads(
                tool_call["function"]["arguments"]
            )

            print(
                f"\nExecuting Tool: {tool_name}"
            )

            result = available_tools[
                tool_name
            ](**args)

            # ------------------------------------------------
            # THIS IS WHERE UI EVENTS WOULD BE EMITTED
            # ------------------------------------------------

            ui_actions = result.get(
                "ui_actions",
                []
            )

            for action in ui_actions:

                print(
                    "\nUI ACTION:",
                    json.dumps(
                        action,
                        indent=2
                    )
                )

            # ------------------------------------------------

            messages.append({
                "role": "tool",

                "tool_call_id":
                    tool_call["id"],

                "content":
                    json.dumps(result)
            })


# =====================================================
# MAIN LOOP
# =====================================================

print("RoyalPMS Assistant")

while True:

    user_input = input("\nYou: ")

    if user_input.lower() == "exit":
        break

    messages.append({
        "role": "user",
        "content": user_input
    })

    process_ai()