import logging
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Add the current directory to sys.path so we can import shared modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.trader import run_trading_cycle

# Configure logging to see output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    print("--- Starting Test Cycle ---")
    print("Note: If COSMOS_DB_CONNECTION_STRING is not set, this will run in fallback mode (no persistence).")
    
    # Set dummy env vars to avoid crashes if they are totally missing
    if "COSMOS_DB_CONNECTION_STRING" not in os.environ:
        logging.warning("COSMOS_DB_CONNECTION_STRING not set. Cosmos DB operations will be skipped/mocked.")
    
    if "GROQ_API_KEY" not in os.environ:
        logging.warning("GROQ_API_KEY not set. OpenAI calls will fail or return defaults.")

    try:
        run_trading_cycle()
        print("--- Test Cycle Completed Successfully ---")
    except Exception as e:
        print(f"--- Test Cycle Failed with Error: {e} ---")
        raise
