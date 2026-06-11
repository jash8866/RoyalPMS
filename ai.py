import os
import json
import requests
from dbcon import *
from aitools import *

#==================DB=========================
db=DatabaseConnection()
db.connect()
db_schema=db.get_database_schema()


#========================CONFIG====================
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEE")
if not NVIDIA_API_KEY:    #raise an error if the API key is not set in the environment
    raise RuntimeError("NVIDIA_API_KEE is not set in the environment")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:    #raise an error if the API key is not set in the environment
    raise RuntimeError("OPENROUTER_API_KEY is not set in the environment")
MODEL = "openai/gpt-oss-120b:free"


# ==================EXTRA SYSTEM PROMPT FOR AI===========================
_SYSTEM_PROMPT = """
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
- Conversations should be strictly regarding the PMS only and should not deviate to other topics.
    """


SYSTEM_PROMPT="""
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
"""
#====================================================


# ================CHAT MEMORY OF MAIN CHATBOT======================


main_memory = [
    {
        "role": "system",
        "content": SYSTEM_PROMPT
    }
]

available_main_tools = {
    "display_table_data": display_table_data,
    "find_relevant_tables": find_relevant_tables
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
            "description": "This tool calls an AI query to find relevant tables in the database. Provide a proper query to the AI and use the results to perform other tool calls effectively.once you get the relevant tables from this tool, call the display_table_data tool to display data from those tables.",
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





# ===================CHATBOT LOOP==================================

def chatbot():
    while True:
        response = call_model(main_memory, main_tools)
        # response = call_nemotron(main_memory, main_tools)
        assistant_message = response["choices"][0]["message"] 

        main_memory.append({
            "role": "assistant",
            "content": assistant_message.get("content"),
            "tool_calls": assistant_message.get("tool_calls"),
            "reasoning_details": assistant_message.get( "reasoning_details" )
        })

        tool_calls = assistant_message.get( "tool_calls" )

        if not tool_calls:
            print( "\nAssistant:", assistant_message.get("content") )
            return

        for tool_call in tool_calls:
            tool_name = (tool_call["function"]["name"]) #get tool name
            args = json.loads( tool_call["function"]["arguments"] )   #

            print( f"\nExecuting Tool: {tool_name}" )

            result = available_main_tools[tool_name](**args)  

            # ------------------------------------------------
            # THIS IS WHERE UI EVENTS WOULD BE EMITTED
            # ------------------------------------------------

            # ui_actions = result.get(
            #     "ui_actions",
            #     []
            # )

            # for action in ui_actions:

            #     print( "\nUI ACTION:", 
            #               json.dumps(
            #                   action,
            #                   indent=2,
            #                   default=str
            #                )
            #           )

            # ------------------------------------------------

            main_memory.append({
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

while True:

    user_input = input("\nYou: ")

    if user_input.lower() == "exit":
        break

    main_memory.append({
        "role": "user",
        "content": user_input
    })

    chatbot()
