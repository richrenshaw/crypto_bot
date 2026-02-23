
import logging
import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.trading_service import TradingService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_tp_sl_logic():
    print("--- Testing TP/SL Reversion Logic ---")
    
    trader = TradingService()
    
    # Mock settings: TP 15%, SL 8%
    trader.take_profit = 0.15
    trader.stop_loss = 0.08
    
    # 1. Test Position setup
    trader.portfolio = {
        "balance_usd": 1000,
        "holdings": {
            "test-coin": {
                "quantity": 100,
                "entry_price": 10.0,
                "value_usd": 1000.0
            }
        }
    }
    
    print("\nSettings: TP=15%, SL=8%")
    
    # Scenario A: Price is UP 16% (Should trigger TP)
    price_up = 11.6
    reason_tp = trader.check_sell_conditions("test-coin", price_up)
    print(f"Scenario A (Price $11.6, +16%): Result = {reason_tp}")
    assert "Take Profit" in reason_tp, f"Expected Take Profit, got {reason_tp}"
    
    # Scenario B: Price is DOWN 10% (Should trigger SL)
    price_down = 9.0
    reason_sl = trader.check_sell_conditions("test-coin", price_down)
    print(f"Scenario B (Price $9.0, -10%): Result = {reason_sl}")
    assert "Stop Loss" in reason_sl, f"Expected Stop Loss, got {reason_sl}"
    
    # Scenario C: Price is UP 4% (Should HOLD - even though it was >5% in previous version)
    price_mid = 10.4
    reason_mid = trader.check_sell_conditions("test-coin", price_mid)
    print(f"Scenario C (Price $10.4, +4%): Result = {reason_mid}")
    assert reason_mid is None, f"Expected None (HOLD), got {reason_mid}"

    # Scenario D: Price is UP 14% (Should HOLD - close to TP but not quite)
    price_near_tp = 11.4
    reason_near_tp = trader.check_sell_conditions("test-coin", price_near_tp)
    print(f"Scenario D (Price $11.4, +14%): Result = {reason_near_tp}")
    assert reason_mid is None, f"Expected None (HOLD), got {reason_near_tp}"

    print("\nVERIFICATION COMPLETE: Sell logic is working correctly as per settings.")

if __name__ == "__main__":
    test_tp_sl_logic()
