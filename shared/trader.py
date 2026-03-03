import logging
import os
import time
from datetime import datetime, timedelta
from shared.trading_service import TradingService
from shared.coingecko_service import BinanceService, CoinGeckoDiscovery
from shared.openai_service import get_trading_signal, evaluate_holding_target
from shared.dexscreener_service import DexScreenerService

def run_trading_cycle():
    logging.info("Starting trading cycle...")
    
    try:
        trader = TradingService()
        cg = BinanceService()
        cgd = CoinGeckoDiscovery()
        
        # 1. Volatile Coin Discovery (Hybrid Mode - Every 2 Hours)
        last_discovery_str = trader.settings.get("LAST_DISCOVERY_TIME")
        last_discovery = None
        if last_discovery_str:
            try:
                last_discovery = datetime.fromisoformat(last_discovery_str)
            except:
                pass

        volatile_coins = []
        if not last_discovery or datetime.utcnow() - last_discovery > timedelta(hours=2):
            logging.info("Running CoinGecko discovery (2h interval reached)...")
            candidates = cgd.get_trending_candidates(min_volume=1000000, limit=10)
            
            new_additions = False
            for cand in candidates:
                coin_symbol = cand["coin"]
                # Check if exists on Binance
                if cg._get_symbol(coin_symbol):
                    volatile_coins.append(coin_symbol)
                    
            logging.info(f"Top volatile coins discovered on Binance: {volatile_coins}")
            
            # Update last discovery time
            trader.settings["LAST_DISCOVERY_TIME"] = datetime.utcnow().isoformat()
            trader.cosmos.update_settings(trader.settings)
        else:
            logging.info("Skipping CoinGecko discovery (within 2h interval).")
        
        # 2. Status Update & Daily Holding Target Review
        logging.info(f"Current USD Balance: ${trader.portfolio['balance_usd']:.2f}")
        holdings_list = list(trader.portfolio['holdings'].keys())
        logging.info(f"Current holdings: {holdings_list}")

        last_review_str = trader.settings.get("LAST_TARGET_REVIEW_TIME")
        last_review = None
        if last_review_str:
            try:
                last_review = datetime.fromisoformat(last_review_str)
            except:
                pass

        if holdings_list and (not last_review or datetime.utcnow() - last_review > timedelta(hours=24)):
            logging.info("Running daily target profit review for holdings...")
            for h_coin in holdings_list:
                h_data = trader.portfolio['holdings'][h_coin]
                current_price = cg.get_current_price(h_coin)
                if current_price == 0: continue
                
                ohlc = cg.get_ohlc(h_coin)
                target_pct = h_data.get("target_profit_pct", trader.settings.get("TAKE_PROFIT", 15))
                
                review_prompt = f"You are reviewing an open position for {h_coin}.\n"
                review_prompt += f"Entry Price: ${h_data['entry_price']:.4f}\n"
                review_prompt += f"Current Price: ${current_price:.4f}\n"
                review_prompt += f"Current Target Profit: {target_pct}%\n"
                review_prompt += f"Recent OHLC (last 30 intervals): {ohlc[-30:]}\n"
                review_prompt += "Is the current target still realistic given the recent trend? If momentum is slowing or dropping hard, lower it. If pumping, maybe raise it or keep it."
                
                eval_res = evaluate_holding_target(review_prompt)
                if eval_res.get("action") == "ADJUST" and eval_res.get("new_target_pct"):
                    new_pct = float(eval_res["new_target_pct"])
                    logging.info(f"LLM adjusted target for {h_coin} from {target_pct}% to {new_pct}%")
                    h_data["target_profit_pct"] = new_pct
                    trader.portfolio["holdings"][h_coin] = h_data
                    trader.update_holding_stats(h_coin, current_price)
                
                time.sleep(10) # Rate limiting
                
            trader.settings["LAST_TARGET_REVIEW_TIME"] = datetime.utcnow().isoformat()
            trader.cosmos.update_settings(trader.settings)
        else:
            logging.info("Skipping daily target review (within 24h interval).")

        # Summary of current performance (Optional/Logging only)
        if holdings_list:
            prices = {cid: cg.get_current_price(cid) for cid in holdings_list}
            cost, net_val, gain_pct = trader.get_portfolio_performance(prices)
            logging.info(f"Portfolio Status: Cost: ${cost:.2f}, Net Value (after fees): ${net_val:.2f}, Gain: {gain_pct:.2f}%")
        # ----------------------------------------
        
        # 3. Watchlist Discovery with DexScreener
        try:
            dex_service = DexScreenerService()
            trending_sol = dex_service.get_trending_solana(limit=15)
            logging.info(f"Discovered {len(trending_sol)} trending solana coins.")
            for pair_data in trending_sol:
                coin_symbol = pair_data['coin']
                # Check if in holdings
                if coin_symbol in trader.portfolio.get('holdings', {}):
                    continue
                # Check if in watchlist
                if trader.cosmos.get_watchlist_item(coin_symbol):
                    continue
                    
                # Not present, upsert to watchlist
                now_str = datetime.now().isoformat()
                watchlist_doc = {
                    "id": f"{coin_symbol}-{pair_data['pairAddress']}",
                    "coin": coin_symbol,
                    "chainId": pair_data['chainId'],
                    "pairAddress": pair_data['pairAddress'],
                    "priceUsd": pair_data['priceUsd'],
                    "liquidityUsd": pair_data['liquidityUsd'],
                    "volume24h": pair_data['volume24h'],
                    "priceChange5m": pair_data['priceChange5m'],
                    "priceChange1h": pair_data['priceChange1h'],
                    "buys24h": pair_data['buys24h'],
                    "sells24h": pair_data['sells24h'],
                    "gtScore": pair_data['gtScore'],
                    "addedAt": now_str,
                    "status": "pending",
                    "notes": ""
                }
                trader.cosmos.upsert_watchlist_item(watchlist_doc)
        except Exception as e:
            logging.error(f"Error during DexScreener watchlist discovery: {e}")
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

                # Refresh holding stats (price/URL) if we own it
                trader.update_holding_stats(coin_id, current_price)

                coin_name = market_data.get("name", coin_id)
                
                # Context Awareness: Are we already holding this?
                holding_info = "Status: Not currently holding."
                if coin_id in trader.portfolio["holdings"]:
                    holding = trader.portfolio["holdings"][coin_id]
                    perf = trader.get_coin_performance(coin_id, current_price)
                    holding_info = f"Status: HOLDING. Entry: ${holding['entry_price']:.4f}, Current P/L: {perf:.2f}%"

                prompt = prompt_template.format(
                    coin_name=coin_name, 
                    current_price=current_price,
                    holding_info=holding_info
                )
                # Append OHLC data to prompt - use 30 for better trend analysis
                prompt += f"\nOHLC Data (last 30 intervals): {ohlc[-30:]} "

                signal_data = get_trading_signal(prompt)
                signal = signal_data.get("action", "HOLD")
                target_profit = signal_data.get("target")
                
                logging.info(f"Signal for {coin_id}: {signal} (Target: {target_profit}%)")
                
                # Rate limiting: 10s delay between Groq calls
                time.sleep(10)
                
                sell_reason = trader.check_sell_conditions(coin_id, current_price)
                
                if sell_reason:
                    trader.simulate_sell(coin_id, current_price, sell_reason)
                elif signal == "BUY":
                    if coin_id not in trader.portfolio["holdings"]:
                        trader.simulate_buy(coin_id, current_price, target_profit)
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
