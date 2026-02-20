import os
import logging
from azure.cosmos import CosmosClient, PartitionKey
from datetime import datetime

# Silence verbose Azure SDK logging
logging.getLogger("azure.cosmos").setLevel(logging.WARNING)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)

class CosmosDBService:
    def __init__(self):
        self.connection_string = os.environ.get("COSMOS_DB_CONNECTION_STRING")
        self.database_name = os.environ.get("COSMOS_DB_DATABASE_NAME", "tradingdb")
        
        if not self.connection_string:
            logging.warning("COSMOS_DB_CONNECTION_STRING is not set.")
            self.client = None
            self.database = None
        else:
            try:
                self.client = CosmosClient.from_connection_string(self.connection_string)
                self.database = self.client.create_database_if_not_exists(id=self.database_name)
                self._init_containers()
            except Exception as e:
                logging.error(f"Failed to initialize Cosmos DB: {e}")
                self.client = None

    def _init_containers(self):
        """Initialize containers if they don't exist."""
        if not self.client: return

        # Portfolios container - Partition Key: /id (we only have one portfolio for now)
        self.portfolios_container = self.database.create_container_if_not_exists(
            id="portfolio",
            partition_key=PartitionKey(path="/id"),
            offer_throughput=400
        )

        # Trades container - Partition Key: /coin
        self.trades_container = self.database.create_container_if_not_exists(
            id="trades",
            partition_key=PartitionKey(path="/coin"),
            offer_throughput=400
        )
        
        # Settings container - Partition Key: /id
        self.settings_container = self.database.create_container_if_not_exists(
            id="settings",
            partition_key=PartitionKey(path="/id"),
            offer_throughput=400
        )

        # Equity logs container - Partition Key: /year (for basic partitioning)
        self.equity_container = self.database.create_container_if_not_exists(
            id="equity_logs",
            partition_key=PartitionKey(path="/year"),
            offer_throughput=400
        )

    def get_portfolio(self):
        """Retrieve the portfolio state."""
        if not self.client:
            return {"holdings": {}, "balance_usd": 1000, "id": "main_portfolio"}
            
        try:
            # We assume a single portfolio with id='main_portfolio'
            item = self.portfolios_container.read_item(item="main_portfolio", partition_key="main_portfolio")
            return item
        except Exception:
            # Initialize if not found
            initial_portfolio = {"id": "main_portfolio", "holdings": {}, "balance_usd": 1000}
            self.portfolios_container.create_item(body=initial_portfolio)
            return initial_portfolio

    def save_portfolio(self, portfolio_data):
        """Save the portfolio state."""
        if not self.client: return
        
        # Ensure ID is present
        if "id" not in portfolio_data:
            portfolio_data["id"] = "main_portfolio"
            
        self.portfolios_container.upsert_item(body=portfolio_data)
        logging.info("Portfolio updated in Cosmos DB.")

    def log_trade(self, trade_data):
        """Log a trade event."""
        if not self.client: return
        
        # Ensure unique ID and timestamp
        if "id" not in trade_data:
            trade_data["id"] = str(datetime.now().timestamp())
        
        self.trades_container.create_item(body=trade_data)
        logging.info(f"Trade logged to Cosmos DB: {trade_data.get('action')} {trade_data.get('coin')}")

    def get_settings(self):
        """Retrieve application settings."""
        default_settings = {
            "id": "main_settings",
            "TAKE_PROFIT": 15,
            "STOP_LOSS": 8,
            "ORDER_AMOUNT": 50,
            "COINS_TO_TRACK": ["bitcoin", "ethereum", "solana", "pepe", "bonk"],
            "PROMPT_TEMPLATE": "You are an aggressive crypto trader chasing volatile opportunities for quick marginal gains. Analyze this OHLC data for {coin_name} over the last 30 days. Current price: ${current_price}. \nSpot potential pumps, high volatility spikes, or momentum shifts—even if risky. Embrace hype if volume supports it; aim for 3-10% swings.\nDecide: BUY (if any upside potential soon), SELL (only on clear downturn), or HOLD (only if flat).\nLook at the data and decide immediately.\nRespond ONLY with one word: BUY, SELL, or HOLD.\nNo explanation, no punctuation, nothing else."
        }

        if not self.client:
            return default_settings

        try:
            item = self.settings_container.read_item(item="main_settings", partition_key="main_settings")
            # Merge with defaults to ensure all keys exist
            return {**default_settings, **item}
        except Exception:
            self.settings_container.create_item(body=default_settings)
            return default_settings

    def log_equity(self, equity_data):
        """Log equity point."""
        if not self.client: return
        
        if "id" not in equity_data:
            equity_data["id"] = str(datetime.now().timestamp())
        
        # Add year for partitioning
        equity_data["year"] = str(datetime.now().year)
        
        self.equity_container.create_item(body=equity_data)
        logging.info(f"Equity point logged to Cosmos DB: ${equity_data.get('total_value')}")
