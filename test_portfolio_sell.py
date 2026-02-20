
import logging
import sys
import os
from unittest.mock import MagicMock

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.trading_service import TradingService
from shared.trader import run_trading_cycle

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_profit_selloff():
    print("--- Testing Portfolio Profit Sell-off ---")
    
    # Mock TradingService and CoinGeckoService
    trader = TradingService()
    
    # Setup a mock portfolio: 1 BTC bought at $50k ($50 cost)
    trader.portfolio = {
        "balance_usd": 1000,
        "holdings": {
            "bitcoin": {
                "quantity": 0.001,
                "entry_price": 50000,
                "value_usd": 50
            }
        }
    }
    
    # Mock prices: BTC is now $60k (+20% gain)
    # Net value = 0.001 * 60000 * 0.99 = 60 * 0.99 = 59.4
    # Gain = (59.4 - 50) / 50 = 9.4 / 50 = 18.8%
    mock_prices = {"bitcoin": 60000}
    
    cost, net_val, gain_pct = trader.get_portfolio_performance(mock_prices)
    print(f"Cost: {cost}, Net Val: {net_val}, Gain: {gain_pct:.2f}%")
    
    if gain_pct >= 5.0:
        print("PASS: Threshold check working")
    else:
        print("FAIL: Threshold check failed")
        
    # Test close all
    trader.simulate_sell = MagicMock()
    trader.close_all_positions(mock_prices)
    
    if trader.simulate_sell.called:
        print("PASS: simulate_sell was called for portfolio TP")
        call_args = trader.simulate_sell.call_args[0]
        if call_args[2] == "Portfolio TP":
             print("PASS: Correct reason 'Portfolio TP' used")
        else:
             print(f"FAIL: Wrong reason {call_args[2]}")
    else:
        print("FAIL: simulate_sell was not called")

if __name__ == "__main__":
    test_profit_selloff()
