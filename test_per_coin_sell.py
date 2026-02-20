
import logging
import sys
import os
from unittest.mock import MagicMock

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.trading_service import TradingService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_per_coin_selloff():
    print("--- Testing Per-Coin Profit Sell-off ---")
    
    trader = TradingService()
    
    # Setup mock portfolio:
    # 1. Bitcoin: Cost $50, current net value $59.4 (Gain: 18.8%) -> SHOULD SELL
    # 2. Ethereum: Cost $50, current net value $51.0 (Gain: 2.0%) -> SHOULD HOLD
    trader.portfolio = {
        "balance_usd": 1000,
        "holdings": {
            "bitcoin": {
                "quantity": 0.001,
                "entry_price": 50000,
                "value_usd": 50
            },
            "ethereum": {
                "quantity": 0.02,
                "entry_price": 2500,
                "value_usd": 50
            }
        }
    }
    
    # Prices: BTC $60k, ETH $2575.75
    # BTC Net: (0.001 * 60000 * 0.99) = 59.4. Gain: 18.8%
    # ETH Net: (0.02 * 2575.75 * 0.99) = 50.999... Gain: ~2%
    mock_prices = {
        "bitcoin": 60000,
        "ethereum": 2575.75
    }
    
    print("\nChecking Bitcoin performance:")
    btc_gain = trader.get_coin_performance("bitcoin", mock_prices["bitcoin"])
    print(f"BTC Gain: {btc_gain:.2f}%")
    
    print("\nChecking Ethereum performance:")
    eth_gain = trader.get_coin_performance("ethereum", mock_prices["ethereum"])
    print(f"ETH Gain: {eth_gain:.2f}%")
    
    # Test individual sell conditions
    print("\nChecking sell conditions:")
    btc_cond = trader.check_sell_conditions("bitcoin", mock_prices["bitcoin"])
    eth_cond = trader.check_sell_conditions("ethereum", mock_prices["ethereum"])
    
    print(f"BTC Condition: {btc_cond}")
    print(f"ETH Condition: {eth_cond}")
    
    if btc_cond and "Profit Taking" in btc_cond:
        print("PASS: Bitcoin profit taking triggered")
    else:
        print("FAIL: Bitcoin profit taking NOT triggered")
        
    if eth_cond is None:
        print("PASS: Ethereum held (below threshold)")
    else:
        print(f"FAIL: Ethereum sell triggered unexpectedly: {eth_cond}")

if __name__ == "__main__":
    test_per_coin_selloff()
