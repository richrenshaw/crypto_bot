import requests
import logging
import time

class DexScreenerService:
    BASE_URL = "https://api.dexscreener.com/latest/dex"

    def get_trending_solana(self, limit=10):
        """Fetch trending (boosted) tokens, filter for Solana, and return up to `limit`."""
        # Using token-boosts as a proxy for trending/volatile
        url = "https://api.dexscreener.com/token-boosts/latest/v1"
        try:
            time.sleep(0.5)
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            boosts = response.json()
            
            # Filter for solana
            sol_tokens = []
            for item in boosts:
                if item.get("chainId") == "solana":
                    token_addr = item.get("tokenAddress")
                    if token_addr and token_addr not in sol_tokens:
                        sol_tokens.append(token_addr)
                        
            if not sol_tokens:
                return []
                
            # Get data for top 'limit' tokens
            top_tokens = sol_tokens[:limit]
            tokens_to_fetch = ",".join(top_tokens)
            
            pairs_url = f"{self.BASE_URL}/tokens/{tokens_to_fetch}"
            time.sleep(0.5)
            pairs_resp = requests.get(pairs_url, timeout=10)
            pairs_resp.raise_for_status()
            
            pairs_data = pairs_resp.json().get("pairs", [])
            
            results = []
            seen_tokens = set()
            
            for pair in pairs_data:
                # DexScreener can return multiple pairs for the same token, take the most liquid one
                token_addr = pair.get("baseToken", {}).get("address")
                
                if token_addr in seen_tokens:
                    continue
                    
                seen_tokens.add(token_addr)
                
                coin_symbol = pair.get("baseToken", {}).get("symbol", "").lower()
                if coin_symbol.endswith("usdt"):
                    coin_symbol = coin_symbol[:-4]
                    
                txns = pair.get("txns", {}).get("h24", {})
                
                results.append({
                    "coin": coin_symbol,
                    "chainId": pair.get("chainId"),
                    "pairAddress": pair.get("pairAddress"),
                    "priceUsd": float(pair.get("priceUsd", 0) or 0),
                    "liquidityUsd": float(pair.get("liquidity", {}).get("usd", 0) or 0),
                    "volume24h": float(pair.get("volume", {}).get("h24", 0) or 0),
                    "priceChange5m": float(pair.get("priceChange", {}).get("m5", 0) or 0),
                    "priceChange1h": float(pair.get("priceChange", {}).get("h1", 0) or 0),
                    "buys24h": txns.get("buys", 0),
                    "sells24h": txns.get("sells", 0),
                    "gtScore": 0  # Placeholder, not natively provided by this DexScreener endpoint
                })
                
                if len(results) >= limit:
                    break
                    
            return results
        except Exception as e:
            logging.error(f"DexScreener trending fetch failed: {e}")
            return []

    def get_pair_details(self, chainId, pairAddress):
        """Returns full pair data for one pool"""
        url = f"{self.BASE_URL}/pairs/{chainId}/{pairAddress}"
        try:
            time.sleep(0.5)
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "pairs" in data and len(data["pairs"]) > 0:
                return data["pairs"][0]
            return None
        except Exception as e:
            logging.error(f"DexScreener pair fetch failed: {e}")
            return None
