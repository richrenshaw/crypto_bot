# test_gemini.py
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()  # Loads variables from .env

client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

try:
    response = client.chat.completions.create(
        model="gemini-2.5-flash",  # Or try "gemini-2.5-flash" if available in your region
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Gemini connection successful!' if this works."}
        ],
        max_tokens=30,
        temperature=0.7,
    )

    print("Success! Gemini responded:")
    print(response.choices[0].message.content.strip())

except Exception as e:
    print("Error occurred:")
    print(e)