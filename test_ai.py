import os
import json
from aitools import *

# ========================CONFIG====================
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEE")
if not NVIDIA_API_KEY:
    raise RuntimeError("NVIDIA_API_KEE is not set in the environment")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY is not set in the environment")

MODEL = "openai/gpt-oss-20b:free"

SYSTEM_PROMPT = """
You are an agent within a Property Management System (PMS) called RoyalPMS.
Your role is to carryout tasks instructed by users and perform actions within the PMS.
You have access to a set of tools that allow you to interact with the PMS and perform various operations.

Rules:
- Always use the tools when you need to perform an action within the PMS
- Provide clear and concise responses/report of your actions to the user.
- If you are unsure about a query, ask the user for clarification don't guess 
- Never perform deletion operations even if the user insists.
- Conversations should be strictly regarding the PMS only and should not deviate to other topics.
- Do not display the database schema to the user but use it to understand how to use the tools effectively and interact with the database when needed.
- Strictly adhere to the structure of the tools when using them and ensure that the arguments passed to the tools are accurate and correct based on their descriptions.
- Display results from tools in a tabular format when the data is tabular and ensure that the presentation of the data is clear and easy to understand for the user.
- Before insert check the table schema and ensure that the data being inserted is valid and complete don't leave any columns null that are not allowed to be null in the schema. If there are any discrepancies or issues with the data, report them to the user and do not perform the insert operation.

Reservation and Booking Rules:
- If a user asks for reserving/booking a room, always calculate the total cost of the booking based on the room type, number of nights, and any additional services requested. Provide a detailed breakdown of the cost to the user before proceeding with the booking.
- Keep the status column in reservations table null.
- Also insert into the reservation_rooms table if a user makes a reservation for a room. Ensure that the room_id and reservation_id are correctly linked in the reservation_rooms table.
- When inserting a new guest always ask for their date of birth, gender, phone number, and email address.

UI Formatting: You must output your final response as a strictly valid JSON object. The JSON must contain two keys: "message" and "table_data".

    "message": A polite, conversational reply formatted in Markdown. CRITICAL: If you are returning database records, do NOT draw a Markdown table inside this message. Just provide a brief conversational summary.

    "table_data": An array of objects containing the raw database results, or null if no database query was made.
"""

available_main_tools = {
    "display_table_data": display_table_data,
    "find_relevant_tables": find_relevant_tables,
    "insert_into_table": insert_into_table
}

main_tools = [
    {
        "type": "function",
        "function": {
            "name": "display_table_data",
            "description": "Display data from any table in the database. The AI should specify the table name and any filters if needed in the arguments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string"},
                    "filters": {
                        "type": "object",
                        "description": "Key-value pairs for filtering the data, where the key is the column name and the value is the filter value."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_relevant_tables",
            "description": "This tool calls an AI query to find relevant tables in the database. Provide a proper query to the AI and use the results to perform other tool calls effectively.once you get the relevant tables from this tool, call the display_table_data tool to display data from those tables.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "insert_into_table",
            "description": "This tool calls an AI query to insert data into a specified table in the database. Provide the table name and the data to be inserted. if it returns an error then read the error message and try to fix the data and call the tool again. If you are unable to fix the data, report the issue to the user and do not perform the insert operation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string"},
                    "data": {"type": "object"}
                }
            }
        }
    }
]

# =================== CORE AI LOOP ==================================

def get_ai_response(session_memory: list, user_message: str) -> str:
    """
    Takes the conversation history and the new user message, 
    processes tool calls, and returns the final AI text response.
    """
    session_memory.append({
        "role": "user",
        "content": user_message
    })

    while True:
        response = call_model(session_memory, main_tools)
        assistant_message = response["choices"][0]["message"] 

        session_memory.append({
            "role": "assistant",
            "content": assistant_message.get("content"),
            "tool_calls": assistant_message.get("tool_calls"),
            "reasoning_details": assistant_message.get("reasoning_details")
        })

        tool_calls = assistant_message.get("tool_calls")

        # If no tools are called, the AI is talking to the user. Break the loop.
        if not tool_calls:
            return assistant_message.get("content")

        # Execute tools if requested
        for tool_call in tool_calls:
            tool_name = tool_call["function"]["name"]
            args = json.loads(tool_call["function"]["arguments"])

            print(f"\nExecuting Tool: {tool_name}")

            if tool_name in available_main_tools:
                result = available_main_tools[tool_name](**args)  
            else:
                result = {"error": f"Tool '{tool_name}' not found"}

            session_memory.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": json.dumps(result, default=str)
            })