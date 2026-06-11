import requests
from dbcon import *
import os 

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEE")
if not NVIDIA_API_KEY:    #raise an error if the API key is not set in the environment
    raise RuntimeError("NVIDIA_API_KEE is not set in the environment")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:    #raise an error if the API key is not set in the environment
    raise RuntimeError("OPENROUTER_API_KEY is not set in the environment")
MODEL = "openai/gpt-oss-120b:free"
# ========================TOOL IMPLEMENTATIONS=============================

   
# ===============STANDALONE OPENROUTER CALL=======================

def call_model(messages, tools):

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

def call_nemotron(messages, tools):
    from openai import OpenAI

    client = OpenAI(
    base_url = "https://integrate.api.nvidia.com/v1",
    api_key = NVIDIA_API_KEY
    )


    response = client.chat.completions.create(
        model="nvidia/nemotron-3-ultra-550b-a55b",
        messages=messages,
        tools=tools,
        tool_choice="auto",
        temperature=1,
        top_p=0.95,
        max_tokens=16384,
        extra_body={"chat_template_kwargs":{"enable_thinking":True},"reasoning_budget":16384},
    )

    return response.model_dump()


def display_table_data(table_name, filters=None):
    db=DatabaseConnection()
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

def find_relevant_tables(query="Just respond query not received from main chatbot"):
    MODEL = "openai/gpt-oss-120b:free"
    db=DatabaseConnection()
    db.connect()
    db_schema = db.get_database_schema()
    MODEL_PROMPT = f"""
    You are a database routing assistant. 
        Here is a map of our database tables: {db_schema}
        
        The user asked: "{query}"

        -Response should be strictly based on the database schema provided and should not include any assumptions or information that is not present in the schema.
        Return a JSON array of the table names and their columns needed to answer this request. 
        Output ONLY valid JSON, nothing else. Example: ["table1":[column1, column2], "table2":[column1]]
        -Don't include your reasoning or any explanations, just the JSON output with relevant tables and columns.
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
    # print("RESPONSE>CHOICES",response.json()["choices"][0]["message"])
    return response.json()["choices"][0]["message"]





