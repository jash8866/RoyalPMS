from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# Best Practice: Load the API key from environment variables
api_key = os.getenv("NVIDIA_API_KEY", "your_fallback_api_key_here")

client = OpenAI(
  base_url = "https://integrate.api.nvidia.com/v1",
  api_key = os.getenv(api_key)
)

def talk(msg: str):
    completion = client.chat.completions.create(
        model="z-ai/glm-5.1",
        messages=[{"role":"user","content":msg}],
        temperature=1,
        top_p=1,
        max_tokens=16384,
        stream=True
    )

    for chunk in completion:
        if not getattr(chunk, "choices", None):
            continue
        if len(chunk.choices) == 0 or getattr(chunk.choices[0], "delta", None) is None:
            continue
        delta = chunk.choices[0].delta
        if getattr(delta, "content", None) is not None:
            # YIELD the content instead of printing it
            yield delta.content