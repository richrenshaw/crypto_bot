from openai import OpenAI
import os
import logging

client = None

def get_client():
    global client
    if client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logging.warning("GROQ_API_KEY not set. internal client will remain None.")
            return None
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1"
        )
    return client

def get_trading_signal(prompt):
    try:
        current_client = get_client()
        if not current_client:
            logging.warning("No OpenAI client available (missing API key). Defaulting to HOLD.")
            return "HOLD"

        response = current_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Decide now: BUY, SELL or HOLD only."}
            ],
            max_tokens=20,
            temperature=0.0,
        )

        content = response.choices[0].message.content
        if content is None or not content.strip():
            logging.warning("Warning: Empty response from Groq → defaulting to HOLD")
            return "HOLD"

        cleaned = content.strip().upper()
        if cleaned in ["BUY", "SELL", "HOLD"]:
            return cleaned
        else:
            logging.warning(f"Unexpected output: '{cleaned}' → defaulting to HOLD")
            return "HOLD"

    except Exception as e:
        logging.error(f"Groq API error: {e}")
        return "HOLD"
