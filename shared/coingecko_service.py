import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException

class BinanceService:
    def __init__(self):
        self.client = Client()  # public client, no API key needed
        self.coin_mapping = {
            "btc": "BTCUSDT",
            "eth": "ETHUSDT",
            "sol": "SOLUSDT",
            "pepe": "PEPEUSDT",
            "bonk": "BONKUSDT",
            "dogwifhat": "WIFUSDT",
            "floki": "FLOKIUSDT",
            "shib": "SHIBUSDT",
            # Add more mappings here as needed
        }

    def _get_symbol(self, coin_id: str) -> str:
        symbol = self.coin_mapping.get(coin_id.lower())
        if not symbol:
            logging.error(f"No Binance mapping for {coin_id}")
            return None
        return symbol

    def get_current_price(self, coin_id: str) -> float:
        symbol = self._get_symbol(coin_id)
        if not symbol:
            return 0.0
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker["price"])
        except Exception as e:
            logging.error(f"Price error for {coin_id}: {e}")
            return 0.0

    def get_ohlc(self, coin_id: str, days: int = 30) -> list:
        symbol = self._get_symbol(coin_id)
        if not symbol:
            return []
        try:
            interval = "1h" if days <= 30 else "4h"
            limit = min(1000, days * 24)
            klines = self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
            return [[int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4])] for k in klines]
        except Exception as e:
            logging.error(f"OHLC error for {coin_id}: {e}")
            return []

    def get_market_data(self, coin_id: str) -> dict:
        symbol = self._get_symbol(coin_id)
        if not symbol:
            return {}
        try:
            ticker24 = self.client.get_ticker(symbol=symbol)
            return {
                "current_price": float(ticker24["lastPrice"]),
                "price_change_percentage_24h": float(ticker24["priceChangePercent"]),
                "total_volume": float(ticker24["quoteVolume"]),
                "high_24h": float(ticker24["highPrice"]),
                "low_24h": float(ticker24["lowPrice"])
            }
        except Exception as e:
            logging.error(f"Market data error for {coin_id}: {e}")
            return {}

    def get_volatile_coins(self, max_cap=500000000, min_vol=100000, min_change=5) -> list:
        try:
            tickers = self.client.get_ticker()
            volatile = []
            for t in tickers:
                if not t["symbol"].endswith("USDT"):
                    continue
                try:
                    change = float(t["priceChangePercent"])
                    vol = float(t["quoteVolume"])
                    if abs(change) >= min_change and vol >= min_vol:
                        coin = t["symbol"].replace("USDT", "").lower()
                        volatile.append(coin)
                except:
                    continue
            volatile.sort(key=lambda x: abs(float(self.get_market_data(x).get("price_change_percentage_24h", 0))), reverse=True)
            return volatile[:10]
        except Exception as e:
            logging.error(f"Volatile coins error: {e}")
            return []
