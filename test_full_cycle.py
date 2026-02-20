
import logging
import sys
import os
from unittest.mock import MagicMock, patch

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging to see output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_full_cycle_with_holdings():
    print("--- Testing Full Trading Cycle with untracked holdings ---")
    
    # We will patch the services to avoid real API calls
    with patch('shared.trader.TradingService') as MockTradingService, \
         patch('shared.trader.CoinGeckoService') as MockCoinGeckoService, \
         patch('shared.trader.get_trading_signal') as MockGetSignal:
        
        # Setup Trader Mock
        trader_instance = MockTradingService.return_value
        trader_instance.portfolio = {
            "balance_usd": 1000,
            "holdings": {
                "bitcoin": { # Bitcoin IS in default track list
                    "quantity": 0.001,
                    "entry_price": 50000,
                    "value_usd": 50
                },
                "untracked-coin": { # This is NOT in default track list
                    "quantity": 100,
                    "entry_price": 1,
                    "value_usd": 100
                }
            }
        }
        trader_instance.settings = {
            "COINS_TO_TRACK": "bitcoin,ethereum"
        }
        
        # Setup CoinGecko Mock
        cg_instance = MockCoinGeckoService.return_value
        cg_instance.get_volatile_coins.return_value = []
        cg_instance.get_market_data.return_value = {"total_volume": 1000000, "name": "Mock Coin"}
        cg_instance.get_ohlc.return_value = [[0,1,1,1]] * 10
        cg_instance.get_current_price.side_effect = lambda cid: 60000 if cid == "bitcoin" else 1.1 if cid == "untracked-coin" else 2000
        
        # Setup Signal Mock
        MockGetSignal.return_value = "HOLD"
        
        # Setup TradingService methods
        from shared.trading_service import TradingService
        real_trader = TradingService()
        real_trader.portfolio = trader_instance.portfolio
        real_trader.settings = trader_instance.settings
        trader_instance.get_coin_performance.side_effect = real_trader.get_coin_performance
        trader_instance.check_sell_conditions.side_effect = real_trader.check_sell_conditions
        trader_instance.get_portfolio_performance.side_effect = real_trader.get_portfolio_performance
        
        # Run the cycle
        from shared.trader import run_trading_cycle
        run_trading_cycle()
        
        print("\nVerification:")
        # Check if untracked-coin was processed
        found_untracked = False
        for call in cg_instance.get_market_data.call_args_list:
            if call[0][0] == "untracked-coin":
                found_untracked = True
                break
        
        if found_untracked:
            print("PASS: 'untracked-coin' was processed in the loop")
        else:
            print("FAIL: 'untracked-coin' was SKIPPED in the loop")

if __name__ == "__main__":
    test_full_cycle_with_holdings()
