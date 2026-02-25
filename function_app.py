import azure.functions as func
import logging
from shared.trader import run_trading_cycle

app = func.FunctionApp()

@app.schedule(schedule="0 */30 * * * *", arg_name="myTimer", run_on_startup=True,
              use_monitor=False) 
def trader_timer(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('The timer is past due!')

    logging.info('Python timer trigger function started.')
    
    try:
        run_trading_cycle()
    except Exception as e:
        logging.error(f"Error running trading cycle: {e}")
    
    logging.info('Python timer trigger function finished.')

@app.route(route="ForceBuy", auth_level=func.AuthLevel.FUNCTION)
def ForceBuy(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('ForceBuy HTTP trigger triggered.')
    coin = req.params.get('coin')
    
    if not coin:
        return func.HttpResponse("Please pass a ?coin= parameter.", status_code=400)
    
    try:
        from shared.trading_service import TradingService
        from shared.coingecko_service import BinanceService
        import json
        
        trader = TradingService()
        binance = BinanceService()
        
        # 1. Get current price
        current_price = binance.get_current_price(coin)
        if current_price <= 0:
            return func.HttpResponse(f"Could not fetch a valid price for {coin}.", status_code=400)
            
        # 2. Execute market buy
        success = trader.simulate_buy(coin, current_price)
        
        if success:
            # 3. Update watchlist document status to "bought" if it exists
            item = trader.cosmos.get_watchlist_item(coin)
            if item:
                item['status'] = 'bought'
                trader.cosmos.upsert_watchlist_item(item)
            
            return func.HttpResponse(
                json.dumps({"success": True, "message": f"Successfully bought {coin} at ${current_price}"}), 
                mimetype="application/json", 
                status_code=200
            )
        else:
            return func.HttpResponse(
                json.dumps({"success": False, "message": f"Failed to buy {coin}. Check funds."}), 
                mimetype="application/json", 
                status_code=400
            )
    except Exception as e:
        logging.error(f"Error in ForceBuy: {e}")
        return func.HttpResponse(f"Server error: {e}", status_code=500)

