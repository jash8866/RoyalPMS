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

# SYSTEM_PROMPT = """
# You are an agent within a Property Management System (PMS)
# called RoyalPMS.

# Your role is to carry out tasks instructed by users and
# perform actions within the PMS.

# Rules:
# - Always use tools when PMS data is required.
# - Never invent PMS data.
# - Ask for clarification when needed.
# - Never perform deletion operations.
# - Report actions performed.
# - Conversations should be strictly regarding the PMS only and should not deviate to other topics.
# """

db=DatabaseConnection()
db.connect()
db_schema=db.get_database_schema()
    



# =====================================================
#  DATABASE
# =====================================================
# db = DatabaseConnection(host="localhost", username="root", password="", db_name="royalpms_cryst8000")
# db.connect()
# reservations = db.fetch_reservations()
# guests = db.fetch_guests()
# for guest in guests:
#     print(guest)
#     a=input("...")


# =====================================================
# TOOLS EXPOSED TO AI
# =====================================================

tools = [
    {
        "type": "function",
        "function": {
            "name": "display_table_data",
            "description": "Display data from any table in the database. The AI should specify the table name and any filters if needed in the arguments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string"
                    },
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
            "description": "Find tables and their structures in the database that are relevant to the user's query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string"
                    }
                }
            }
        }
    }


]


# =====================================================
# REAL TOOL IMPLEMENTATIONS
# =====================================================
    
def display_table_data(table_name, filters=None):
    db.connect()
    data = db.fetch_table_data(table_name, filters)
    print(f"Data from {table_name} with filters {filters}:")
    for row in data:
        print(row)
        
    return {
        "success": True,
        "data": data,

        "ui_actions": [
            {
                "type": "display_table",
                "table_name": table_name,
                "data": data
            }
        ]   
    }

def find_relevant_tables(query="find tables for reservations"):
    MODEL = "openai/gpt-oss-120b:free"
    MODEL_PROMPT = f"""
    
    You are a database routing assistant. 
        Here is a map of our database tables: {db_schema}
        
        The user asked: "{query}"

        -Response should be strictly based on the database schema provided and should not include any assumptions or information that is not present in the schema.
        Return a JSON array of the table names needed to answer this request. 
        Output ONLY valid JSON, nothing else. Example: ["table1", "table2"]
    """
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
            "messages": [
                {
                    "role": "system",
                    "content": MODEL_PROMPT
                },
                {
                    "role": "user",
                    "content": query
                }
            ]
        }
    )

    response.raise_for_status()
    print("RESPONSE>CHOICES",response.choices)


available_tools = {
    # "search_reservations": search_reservations,
    "display_table_data": display_table_data
}


SYSTEM_PROMPT="""You are an agent within a Property Management System (PMS) called RoyalPMS.

Your role is to carryout tasks instructed by users and perform actions within the PMS.

You have access to a set of tools that allow you to interact with the PMS and perform various operations.

Here is the exact structure of my database:{db_schema}

Rules:
- Always use the tools when you need to perform an action within the PMS
- Provide clear and concise responses/report of your actions to the user.
- If you are unsure about how to use a tool or need more information, ask the user for clarification don't guess 
- Never perform deletion operations even if the user insists.
- Conversations should be strictly regarding the PMS only and should not deviate to other topics.
-do not display the database schema to the user but use it to understand how to use the tools effectively and interact with the database when needed.
-Strictly adhere to the structure of the tools when using them and ensure that the arguments passed to the tools are accurate and correctly formatted based on the database schema provided.
-disply results from tools in a tabular format when the data is tabular and ensure that the presentation of the data is clear and easy to understand for the user.
"""

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
                        indent=2,
                        default=str
                    )
                )

            # ------------------------------------------------

            messages.append({
                "role": "tool",

                "tool_call_id":
                    tool_call["id"],

                "content":
                    json.dumps(result,default=str)
            })


# =====================================================
# MAIN LOOP
# =====================================================

print("RoyalPMS Assistant")

# while True:

#     user_input = input("\nYou: ")

#     if user_input.lower() == "exit":
#         break

#     messages.append({
#         "role": "user",
#         "content": user_input
#     })

#     process_ai()

find_relevant_tables()