import os
import logging
from datetime import datetime
from .cosmos_db import CosmosDBService

class TradingService:
    def __init__(self):
        self.cosmos = CosmosDBService()
        self.settings = self.cosmos.get_settings()
        
        self.order_amount = float(self.settings.get("ORDER_AMOUNT", 50))
        self.take_profit = float(self.settings.get("TAKE_PROFIT", 15)) / 100
        self.stop_loss = float(self.settings.get("STOP_LOSS", 8)) / 100
        
        # Load portfolio from Cosmos
        self.portfolio = self.cosmos.get_portfolio()

    def simulate_buy(self, coin_id, current_price):
        if self.portfolio["balance_usd"] < self.order_amount:
            logging.info(f"Insufficient funds to buy {coin_id}")
            return False
            
        quantity = self.order_amount / current_price
        self.portfolio["holdings"][coin_id] = {
            "quantity": quantity,
            "entry_price": current_price,
            "value_usd": self.order_amount
        }
        self.portfolio["balance_usd"] -= self.order_amount
        
        # Save updated portfolio to Cosmos
        self.cosmos.save_portfolio(self.portfolio)
        
        logging.info(f"Simulated BUY: {quantity} of {coin_id} at ${current_price}")
        
        self.log_trade(
            action="BUY",
            coin_id=coin_id,
            price=current_price,
            quantity=quantity,
            pnl=None,
            reason="AI signal"
        )
        return True

    def simulate_sell(self, coin_id, current_price, reason):
        if coin_id not in self.portfolio["holdings"]:
            return False
            
        holding = self.portfolio["holdings"][coin_id]
        value = holding["quantity"] * current_price
        # Simulate transaction cost: 1% fee (adjusted from 0.98 to 0.99)
        net_value = value * 0.99
        profit_loss = net_value - holding["value_usd"]
        
        self.portfolio["balance_usd"] += net_value
        del self.portfolio["holdings"][coin_id]
        
        # Save updated portfolio
        self.cosmos.save_portfolio(self.portfolio)
        
        logging.info(f"Simulated SELL: {coin_id} for ${net_value:.2f} ({reason}, P/L: ${profit_loss:.2f})")
        
        self.log_trade(
            action="SELL",
            coin_id=coin_id,
            price=current_price,
            quantity="all",
            pnl=profit_loss,
            reason=reason
        )
        return True

    def get_coin_performance(self, coin_id, current_price):
        """Calculate the gain/loss for a specific coin holding."""
        if coin_id not in self.portfolio.get("holdings", {}):
            return 0
            
        holding = self.portfolio["holdings"][coin_id]
        cost = holding.get("value_usd", 0)
        quantity = holding.get("quantity", 0)
        
        # Current net value if sold now (after 1% fee)
        net_value = quantity * current_price * 0.99
        gain_pct = ((net_value - cost) / cost) * 100 if cost > 0 else 0
        
        logging.info(f"Evaluating {coin_id}: Current gain/loss: {gain_pct:.2f}% (Market Val after fee: ${net_value:.2f}, Cost: ${cost:.2f})")
        return gain_pct

    def get_portfolio_performance(self, current_prices):
        """Calculate portfolio performance against current market prices."""
        total_cost = 0
        total_net_value = 0
        
        holdings = self.portfolio.get("holdings", {})
        if not holdings:
            return 0, 0, 0
            
        for coin_id, holding in holdings.items():
            cost = holding.get("value_usd", 0)
            quantity = holding.get("quantity", 0)
            current_price = current_prices.get(coin_id, 0)
            
            if current_price == 0:
                # If price missing, assume no change for safety or skip
                current_price = holding.get("entry_price", 0)
                
            total_cost += cost
            # Account for 1% sell fee in net value
            total_net_value += (quantity * current_price * 0.99)
            
        net_gain_pct = ((total_net_value - total_cost) / total_cost) * 100 if total_cost > 0 else 0
        return total_cost, total_net_value, net_gain_pct

    def close_all_positions(self, current_prices):
        """Sell all currently held positions."""
        holdings = list(self.portfolio.get("holdings", {}).keys())
        logging.info(f"Closing all {len(holdings)} positions...")
        
        for coin_id in holdings:
            current_price = current_prices.get(coin_id, 0)
            if current_price > 0:
                self.simulate_sell(coin_id, current_price, "Portfolio TP")
            else:
                logging.warning(f"Could not sell {coin_id}: Price missing")

    def check_sell_conditions(self, coin_id, current_price):
        """Check if any sell conditions are met (5% Net Gain or TP/SL)."""
        if coin_id in self.portfolio["holdings"]:
            # 1. First, check the new 5% Net Gain After Fees (as requested)
            gain_pct = self.get_coin_performance(coin_id, current_price)
            if gain_pct >= 5.0:
                return f"Profit Taking ({gain_pct:.2f}% Net Gain after fees)"
            
            # 2. Then check Trailing / Fixed TP/SL from settings
            entry_price = self.portfolio["holdings"][coin_id]["entry_price"]
            if current_price >= entry_price * (1 + self.take_profit):
                return "Take Profit (Fixed 15%)"
            elif current_price <= entry_price * (1 - self.stop_loss):
                return "Stop Loss (Fixed 8%)"
                
        return None
    
    def log_trade(self, action, coin_id, price, quantity, pnl=None, reason=None):
        timestamp = datetime.now().isoformat()
        trade_data = {
            'timestamp': timestamp,
            'action': action,
            'coin': coin_id,
            'price': price,
            'quantity': quantity,
            'pnl': pnl if pnl is not None else '',
            'reason': reason or '',
            'balance_usd': self.portfolio['balance_usd'],
            'total_value': self.get_total_value()
        }
        self.cosmos.log_trade(trade_data)

    def get_total_value(self):
        total = self.portfolio['balance_usd']
        for coin, holding in self.portfolio['holdings'].items():
            total += holding.get('quantity', 0) * holding.get('entry_price', 0)
        return total
    
    def log_equity_curve(self):
        timestamp = datetime.now().isoformat()
        total_value = self.get_total_value()
        
        equity_data = {
            'timestamp': timestamp,
            'total_value': round(total_value, 2),
            'balance_usd': round(self.portfolio['balance_usd'], 2),
            'holdings_count': len(self.portfolio['holdings'])
        }
        self.cosmos.log_equity(equity_data)
