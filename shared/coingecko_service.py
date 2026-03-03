import logging
import time
import requests
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
        coin_id_lower = coin_id.lower()
        if coin_id_lower == "pmpr":
             return None # ignore obviously fake ones or just rely on binance check

        symbol = self.coin_mapping.get(coin_id_lower)
        if not symbol:
            dyn_symbol = f"{coin_id.upper()}USDT"
            try:
                # verify it exists
                self.client.get_symbol_ticker(symbol=dyn_symbol)
                self.coin_mapping[coin_id_lower] = dyn_symbol
                return dyn_symbol
            except Exception:
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


class CoinGeckoDiscovery:
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"

    def get_trending_candidates(self, min_volume=1000000, limit=10):
        try:
            # Sleep 2 seconds to be rate-limit friendly
            time.sleep(2)
            url = f"{self.base_url}/coins/markets"
            params = {
                "vs_currency": "usd",
                "order": "volume_desc",
                "per_page": 100,
                "page": 1,
                "sparkline": False
            }
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            
            candidates = []
            for item in data:
                vol = item.get("total_volume", 0) or 0
                if vol < min_volume:
                    continue
                price_change = abs(item.get("price_change_percentage_24h", 0) or 0)
                # Let's say we want coins with > 5% change in 24h
                if price_change > 5.0:
                    symbol = item.get("symbol", "").lower()
                    if symbol:
                        candidates.append({
                            "coin": symbol,
                            "name": item.get("name"),
                            "priceUsd": item.get("current_price"),
                            "volume24h": vol,
                            "priceChange24h": price_change
                        })
                        if len(candidates) >= limit:
                            break
            return candidates
        except Exception as e:
            logging.error(f"CoinGecko discovery failed: {e}")
            return []
