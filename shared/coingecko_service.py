import requests
import os
import logging

class CoinGeckoService:
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"  # Free tier
        self.headers = {"x-cg-demo-api-key": os.getenv("COINGECKO_API_KEY")}

    def get_coins_list(self):
        url = f"{self.base_url}/coins/list"
        try:
            response = requests.get(url, headers=self.headers)
            return response.json() if response.status_code == 200 else []
        except Exception as e:
            logging.error(f"Error fetching coins list: {e}")
            return []

    def get_ohlc(self, coin_id, days=30):
        url = f"{self.base_url}/coins/{coin_id}/ohlc"
        params = {"vs_currency": "usd", "days": days}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            return response.json() if response.status_code == 200 else []
        except Exception as e:
            logging.error(f"Error fetching OHLC for {coin_id}: {e}")
            return []

    def get_current_price(self, coin_id):
        url = f"{self.base_url}/simple/price"
        params = {"ids": coin_id, "vs_currencies": "usd"}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            data = response.json()
            return data.get(coin_id, {}).get("usd", 0) if response.status_code == 200 else 0
        except Exception as e:
            logging.error(f"Error fetching price for {coin_id}: {e}")
            return 0

    def get_market_data(self, coin_id):
        url = f"{self.base_url}/coins/markets"
        params = {"vs_currency": "usd", "ids": coin_id}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            data = response.json()
            return data[0] if data and response.status_code == 200 else {}
        except Exception as e:
            logging.error(f"Error fetching market data for {coin_id}: {e}")
            return {}
    
    def get_volatile_coins(self, max_cap=500000000, min_vol=100000, min_change=5):
        """Find coins with high 24h volatility within a specific market cap range."""
        url = f"{self.base_url}/coins/markets"
        params = {
            "vs_currency": "usd", 
            "order": "volume_desc", # Start with high volume coins
            "per_page": 100,
            "sparkline": False
        }
        try:
            response = requests.get(url, headers=self.headers, params=params)
            data = response.json()
            
            # Filter for volatility and market cap
            volatile = [
                coin['id'] for coin in data 
                if coin.get('market_cap', 0) < max_cap 
                and abs(coin.get('price_change_percentage_24h', 0)) >= min_change 
                and coin.get('total_volume', 0) > min_vol
            ]
            
            return volatile[:10]  # Return top 10
        except Exception as e:
            logging.error(f"Error fetching volatile coins: {e}")
            return []
