import os
from dotenv import dotenv_values
from google import genai

env_vals = dotenv_values(r"C:\Users\reals\Vin\K5-L3-Day06-DataIngestionEngineering\starter\.env")
api_key = env_vals.get("GEMINI_API_KEY")

if not api_key:
    print("No GEMINI_API_KEY found")
    exit(1)

client = genai.Client(api_key=api_key)

# Test listing or generating a simple test response
for model in ["gemini-3.8-flash", "gemini-3.5-flash", "gemini-3-flash"]:
    try:
        response = client.models.generate_content(
            model=model,
            contents="Say 'Hello Agentic RAG Day 7' in 5 words."
        )
        print(f"Success with model {model}: {response.text.strip()}")
        break
    except Exception as e:
        print(f"Model {model} failed: {e}")
