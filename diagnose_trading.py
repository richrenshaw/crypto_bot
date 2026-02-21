
import logging
import sys
import os
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load local.settings.json values into environment if running locally
import json
try:
    with open("local.settings.json", "r") as f:
        settings = json.load(f)
        for k, v in settings.get("Values", {}).items():
            os.environ[k] = str(v)
except:
    pass

from shared.openai_service import get_trading_signal
from shared.cosmos_db import CosmosDBService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def diagnose_prompt():
    print("--- AI Prompt Diagnostic Tool ---")
    
    # 1. Get current prompt from Cosmos if possible, otherwise local
    cosmos = CosmosDBService()
    settings = cosmos.get_settings()
    prompt_template = settings.get("PROMPT_TEMPLATE")
    
    if not prompt_template:
        template_path = os.path.join("shared", "prompt_template.txt")
        with open(template_path, "r") as f:
            prompt_template = f.read()
        print("Using local prompt template.")
    else:
        print("Using prompt template from Cosmos DB.")

    scenarios = {
        "Bullish Scenario": {
            "price": 65000,
            "ohlc": [[0, 60000, 65000, 59000, 64500]] * 30,
            "desc": "Steady gains, strong volume",
            "holding": "Status: Not currently holding."
        },
        "Bearish Scenario (Crash)": {
            "price": 52000,
            "ohlc": [[0, 65000, 65500, 51000, 52000]] * 30,
            "desc": "Sharp drop from $65k to $52k",
            "holding": "Status: HOLDING. Entry: $65000.00, Current P/L: -20.00%"
        },
        "Flat/Sideways Scenario": {
            "price": 60000,
            "ohlc": [[0, 59900, 60100, 59800, 60000]] * 30,
            "desc": "Price stuck at $60k with low volatility",
            "holding": "Status: Not currently holding."
        },
        "Highly Volatile Scenario": {
            "price": 58000,
            "ohlc": [[0, 50000, 65000, 48000, 58000]] * 30,
            "desc": "Wild swings between $48k and $65k",
            "holding": "Status: Not currently holding."
        }
    }

    print("\nStarting AI diagnostics. Testing 4 scenarios...")

    for name, data in scenarios.items():
        print(f"\n>>> Name: {name}")
        print(f">>> Description: {data['desc']}")
        
        try:
            prompt = prompt_template.format(
                coin_name="Bitcoin", 
                current_price=data['price'],
                holding_info=data['holding']
            )
            prompt += f"\nOHLC Data (last 30 intervals): {data['ohlc']} "
            
            signal = get_trading_signal(prompt)
            print(f">>> AI SIGNAL: {signal}")
            
            # Diagnostic logic
            if name == "Bearish Scenario (Crash)" and signal != "SELL":
                print("!!! ALERT: AI didn't suggest SELL on a crash. Prompt might be too 'HODL' biased.")
            elif name == "Bullish Scenario" and signal == "SELL":
                print("!!! ALERT: AI suggested SELL on a rally. Prompt might be too pessimistic.")
            elif signal not in ["BUY", "SELL", "HOLD"]:
                print(f"!!! ALERT: AI returned invalid signal: {signal}")
            else:
                print("--- AI Response looks reasonable for this scenario.")
        except Exception as e:
            print(f"!!! API ERROR: {e}")

    print("\n--- Diagnostic Complete ---")

if __name__ == "__main__":
    diagnose_prompt()
