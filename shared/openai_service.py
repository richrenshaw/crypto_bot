from openai import OpenAI
import os
import logging
import json

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
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Decide now. You MUST output valid JSON only. Format: {\"action\": \"BUY\", \"target_profit_pct\": 10} or {\"action\": \"SELL\"} or {\"action\": \"HOLD\"}. Give target_profit_pct 3-20 if action is BUY."}
            ],
            response_format={"type": "json_object"},
            max_tokens=60,
            temperature=0.0,
        )

        content = response.choices[0].message.content
        if content is None or not content.strip():
            logging.warning("Warning: Empty response from Groq → defaulting to HOLD")
            return {"action": "HOLD"}

        try:
            data = json.loads(content)
            action = data.get("action", "HOLD").strip().upper()
            target = data.get("target_profit_pct")
            
            if action not in ["BUY", "SELL", "HOLD"]:
                logging.warning(f"Unexpected action: '{action}' → defaulting to HOLD")
                action = "HOLD"
                
            return {"action": action, "target": target}
        except json.JSONDecodeError:
            logging.error(f"Failed to parse JSON: {content}")
            return {"action": "HOLD"}

    except Exception as e:
        logging.error(f"Groq API error: {e}")
        return {"action": "HOLD"}

def evaluate_holding_target(prompt):
    try:
        current_client = get_client()
        if not current_client:
            logging.warning("No OpenAI client available. Defaulting to KEEP.")
            return {"action": "KEEP"}

        response = current_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Review the holding target profit. You MUST output valid JSON only. Format: {\"action\": \"KEEP\"} or {\"action\": \"ADJUST\", \"new_target_pct\": 5}."}
            ],
            response_format={"type": "json_object"},
            max_tokens=60,
            temperature=0.0,
        )

        content = response.choices[0].message.content
        if content is None or not content.strip():
            return {"action": "KEEP"}

        try:
            data = json.loads(content)
            action = data.get("action", "KEEP").strip().upper()
            new_target = data.get("new_target_pct")
            
            if action not in ["KEEP", "ADJUST"]:
                action = "KEEP"
                
            return {"action": action, "new_target_pct": new_target}
        except json.JSONDecodeError:
            logging.error(f"Failed to parse JSON for target evaluation: {content}")
            return {"action": "KEEP"}

    except Exception as e:
        logging.error(f"Groq API error during target evaluation: {e}")
        return {"action": "KEEP"}
