from google.genai import types
from google.genai import types as GenaiTypes
import json

from google import genai
import requests
from dbcon import *
import os 

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEE")
if not NVIDIA_API_KEY:    #raise an error if the API key is not set in the environment
    raise RuntimeError("NVIDIA_API_KEE is not set in the environment")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:    #raise an error if the API key is not set in the environment
    raise RuntimeError("OPENROUTER_API_KEY is not set in the environment")
MODEL = "meta-llama/llama-3.3-70b-instruct:free"

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

from google import genai
from google.genai import types as GenaiTypes

from google import genai
from google.genai import types as GenaiTypes

from google import genai
from google.genai import types as GenaiTypes

def callgem(messages, tools=None):
    # Initialize client (Make sure GEMINI_API_KEY environment variable is set)
    client = genai.Client()
    
    formatted_contents = []
    system_instruction = None

    # 1. Translate OpenAI-style history to Google GenAI requirements
    for msg in messages:
        role = msg.get("role")
        content_text = msg.get("content") or ""
        tool_calls = msg.get("tool_calls")
        
        if role == "system":
            system_instruction = content_text
            continue
            
        # Handle responses from executed tools back to the model
        if role == "tool":
            formatted_contents.append(
                GenaiTypes.Content(
                    role="user",
                    parts=[
                        GenaiTypes.Part.from_function_response(
                            name="unknown_tool", # Optional for flash mapping
                            response={"result": content_text}
                        )
                    ]
                )
            )
            continue

        # Setup parts array
        parts = []
        if content_text:
            parts.append(GenaiTypes.Part.from_text(text=str(content_text)))
            
        # If the history records that the assistant called tools previously
        if tool_calls:
            for tc in tool_calls:
                parts.append(
                    GenaiTypes.Part.from_function_call(
                        name=tc["function"]["name"],
                        args=json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"]
                    )
                )

        gemini_role = "model" if role in ["assistant", "model"] else "user"
        formatted_contents.append(
            GenaiTypes.Content(role=gemini_role, parts=parts)
        )

    # 2. Add System Prompt to generation config
    # Also inject your SYSTEM_PROMPT from the main script if it's not in the loop
    config = GenaiTypes.GenerateContentConfig(
        tools=tools if tools else None,
        system_instruction=system_instruction if system_instruction else SYSTEM_PROMPT
    )

    # 3. Request generation from Gemini
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=formatted_contents,
        config=config
    )

    # 4. Mock an OpenAI Response structure so your orchestration loop remains happy!
    openai_tool_calls = []
    if response.function_calls:
        for i, call in enumerate(response.function_calls):
            openai_tool_calls.append({
                "id": f"call_{i}_{call.name}",
                "type": "function",
                "function": {
                    "name": call.name,
                    "arguments": json.dumps(call.args)
                }
            })

    # This structure returns exactly what your `get_ai_response` expects
    openai_mock_payload = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": response.text if response.text else None,
                    "tool_calls": openai_tool_calls if openai_tool_calls else None
                }
            }
        ]
    }

    return openai_mock_payload

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

        # "ui_actions": [
        #     {
        #         "type": "display_table",
        #         "table_name": table_name,
        #         "data": data
        #     }
        # ]   
    }


def find_relevant_tables(query="Just respond query not received from main chatbot"):
    db = DatabaseConnection()
    db.connect()
    db_schema = db.get_database_schema()
    
    # 1. Initialize the Google GenAI client
    # (It will automatically pick up GEMINI_API_KEY from your environment)
    client = genai.Client()
    
    MODEL_PROMPT = f"""
    You are a database routing assistant. 
    Here is a map of our database tables: {db_schema}
    
    The user asked: "{query}"

    Analyze the user's query and output a valid JSON object mapping table names 
    to arrays of their column names. Only include tables strictly relevant to the user's query.
    """
    
    # 2. Configure Gemini for Strict Structured Output
    config = GenaiTypes.GenerateContentConfig(
        system_instruction=MODEL_PROMPT,
        response_mime_type="application/json",
        # Force the output structure to be an object containing array mappings
        response_schema={
            "type": "OBJECT",
            "description": "Map of table names to lists of their column names.",
            "additional_properties": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            }
        }
    )
    
    # 3. Request generation from the lightweight/fast Flash model
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="Generate the relevant table mappings.",
        config=config
    )
    
    # Optional debugging check: response.text is guaranteed to be a raw JSON string
    print(f"\n[ROUTER DEBUG] Raw model output: {response.text}")
    
    # 4. Mock the exact OpenAI dictionary layout that your main code expects
    result_message = {
        "role": "assistant",
        "content": response.text
    }
    
    return result_message

def insert_into_table(table_name, data):
    db=DatabaseConnection()
    db.connect()
    res=db.insert_into_table(table_name, data)
    return res