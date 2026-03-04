import requests
import logging
import time

class DexScreenerService:
    BASE_URL = "https://api.dexscreener.com/latest/dex"

    def get_trending_solana(self, limit=10):
        """Fetch trending (boosted) tokens, filter for Solana, and return up to `limit`."""
        logging.info("DexScreener trending fetch disabled.")
        return []

    def get_pair_details(self, chainId, pairAddress):
        """Returns full pair data for one pool"""
        logging.info("DexScreener pair fetch disabled.")
        return None
