import logging
import os
from .trading_service import TradingService
from .coingecko_service import CoinGeckoService
from .openai_service import get_trading_signal

def run_trading_cycle():
    logging.info("Starting trading cycle...")
    
    try:
        trader = TradingService()
        cg = CoinGeckoService()
        
        # 1. Volatile Coin Discovery
        volatile_coins = cg.get_volatile_coins()
        logging.info(f"Top volatile coins discovered: {volatile_coins}")
        
        # 2. Status Update
        logging.info(f"Current USD Balance: ${trader.portfolio['balance_usd']:.2f}")
        holdings_list = list(trader.portfolio['holdings'].keys())
        logging.info(f"Current holdings: {holdings_list}")

        # Summary of current performance (Optional/Logging only)
        if holdings_list:
            prices = {cid: cg.get_current_price(cid) for cid in holdings_list}
            cost, net_val, gain_pct = trader.get_portfolio_performance(prices)
            logging.info(f"Portfolio Status: Cost: ${cost:.2f}, Net Value (after fees): ${net_val:.2f}, Gain: {gain_pct:.2f}%")
        # ----------------------------------------
        
        # Load prompt template from settings with fallback to local file
        prompt_template = trader.settings.get("PROMPT_TEMPLATE")
        
        if not prompt_template:
            template_path = os.path.join(os.path.dirname(__file__), "prompt_template.txt")
            if os.path.exists(template_path):
                with open(template_path, "r") as f:
                    prompt_template = f.read()
                logging.info("Using local prompt_template.txt (fallback)")
            else:
                logging.error("Prompt template not found in settings or local file!")
                return
        else:
            logging.info("Using dynamic PROMPT_TEMPLATE from Cosmos DB")

        coins_to_track = trader.settings.get("COINS_TO_TRACK", [])
        if isinstance(coins_to_track, str):
            coins_to_track = [c.strip() for c in coins_to_track.split(",")]
            
        # Merge with dynamically discovered volatile coins
        initial_count = len(coins_to_track)
        for v_coin in volatile_coins:
            if v_coin not in coins_to_track:
                coins_to_track.append(v_coin)
        
        # Merge with current holdings (in case any are not in tracking/volatile lists)
        for h_coin in holdings_list:
            if h_coin not in coins_to_track:
                coins_to_track.append(h_coin)
                
        new_coins_added = len(coins_to_track) - initial_count
        if new_coins_added > 0:
            logging.info(f"Added {new_coins_added} coins (volatile/holdings) to track. Total: {len(coins_to_track)}")

        # Fallback for min volume if not in environment
        min_volume = float(os.getenv("MIN_VOLUME_24H", 100000))

        logging.info(f"Tracking coins: {coins_to_track}")

        for coin_id in coins_to_track:
            try:
                market_data = cg.get_market_data(coin_id)
                if not market_data:
                    logging.warning(f"Skipping {coin_id}: No market data found")
                    continue
                    
                if market_data.get("total_volume", 0) < min_volume:
                    logging.info(f"Skipping {coin_id}: Low volume ({market_data.get('total_volume', 0)})")
                    continue
                
                ohlc = cg.get_ohlc(coin_id)
                if not ohlc:
                    logging.warning(f"Skipping {coin_id}: No OHLC data")
                    continue
                
                current_price = cg.get_current_price(coin_id)
                if current_price == 0:
                    logging.warning(f"Skipping {coin_id}: Invalid price")
                    continue

                coin_name = market_data.get("name", coin_id)
                
                prompt = prompt_template.format(coin_name=coin_name, current_price=current_price)
                # Append OHLC data to prompt
                prompt += f"\nOHLC Data: {ohlc[-5:]} "  # Last 5 candles for brevity

                signal = get_trading_signal(prompt)
                logging.info(f"Signal for {coin_id}: {signal}")
                
                sell_reason = trader.check_sell_conditions(coin_id, current_price)
                
                if sell_reason:
                    trader.simulate_sell(coin_id, current_price, sell_reason)
                elif signal == "BUY":
                    if coin_id not in trader.portfolio["holdings"]:
                        trader.simulate_buy(coin_id, current_price)
                    else:
                        logging.info(f"HOLD for {coin_id}: Already holding a position")
                elif signal == "SELL":
                    if coin_id in trader.portfolio["holdings"]:
                        trader.simulate_sell(coin_id, current_price, "AI Signal")
                    else:
                        logging.info(f"HOLD for {coin_id}: No position to sell")
                else:
                    logging.info(f"HOLD for {coin_id}: Neutral signal")
            except Exception as e:
                logging.error(f"Error processing {coin_id}: {e}")
                continue

        # After processing all coins, log equity
        trader.log_equity_curve()
        logging.info("Trading cycle completed.")
        
    except Exception as e:
        logging.error(f"Critical error in trading cycle: {e}")
