import azure.functions as func
import logging
from shared.trader import run_trading_cycle

app = func.FunctionApp()

@app.schedule(schedule="0 */5 * * * *", arg_name="myTimer", run_on_startup=True,
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
