import random

class BaseAgent:
    def __init__(self, agent_id):
        self.agent_id = agent_id
        self.inventory = 0 

    def create_order(self, side, price, qty):
        return {
            "agent_id": self.agent_id,
            "type": "LIMIT",
            "side": side,
            "price": round(price, 2),
            "qty": qty
        }

class MarketMakerAgent(BaseAgent):
    def on_price_update(self, tick_data):
        current_price = tick_data["current_price"]
        
        if self.inventory > 1000:
            bid_price = current_price - 2.00 
            ask_price = current_price + 0.10
        else:
            bid_price = current_price - 0.10
            ask_price = current_price + 0.10
            
        return [
            self.create_order("BUY", bid_price, 100),
            self.create_order("SELL", ask_price, 100)
        ]

class HedgeFundAgent(BaseAgent):
    def __init__(self, agent_id):
        super().__init__(agent_id)
        self.price_history = []

    def on_price_update(self, tick_data):
        current_price = tick_data["current_price"]
        self.price_history.append(current_price)
        
        if len(self.price_history) > 50:
            self.price_history.pop(0)
            
        if len(self.price_history) == 50:
            moving_average = sum(self.price_history) / 50
            if current_price < (moving_average * 0.95):
                return [self.create_order("BUY", current_price, 5000)]
                
        return []

class MomentumAgent(BaseAgent):
    def on_price_update(self, tick_data):
        current_price = tick_data["current_price"]
        decision = random.choice(["BUY", "SELL", "HOLD", "HOLD"]) 
        
        if decision == "BUY":
            return [self.create_order("BUY", current_price + 0.50, 50)] 
        elif decision == "SELL":
            return [self.create_order("SELL", current_price - 0.50, 50)]
            
        return []

class HistoricalReplayer(BaseAgent):
    def __init__(self, agent_id, historical_dataframe):
        super().__init__(agent_id)
        self.df = historical_dataframe
        self.current_step = 0
        
    def on_price_update(self, tick_data):
        if self.current_step < len(self.df):
            real_historical_price = self.df.iloc[self.current_step]['Close']
            self.current_step += 1
            return [
                self.create_order("BUY", real_historical_price - 0.01, 10000),
                self.create_order("SELL", real_historical_price + 0.01, 10000)
            ]
        return []