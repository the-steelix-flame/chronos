import zmq
import time
import random
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [TRUE_ENGINE] - %(message)s')

class MatchingEngine:
    def __init__(self):
        self.bids = {}  # price -> total_qty
        self.asks = {}  # price -> total_qty
        self.current_price = 2500.50
        self.recent_volume = 10000.0
        
        # RSI Tracking
        self.price_history = [2500.50] * 15 # Need 14 periods for RSI
        
    def add_order(self, action, price, qty):
        # We round price to 2 decimals to simulate "ticks"
        price = round(price, 2)
        if action == "BUY":
            self.bids[price] = self.bids.get(price, 0) + qty
        elif action == "SELL":
            self.asks[price] = self.asks.get(price, 0) + qty

    def calculate_rsi(self):
        if len(self.price_history) < 15:
            return 50.0
            
        gains = 0
        losses = 0
        for i in range(1, 15):
            change = self.price_history[-i] - self.price_history[-(i+1)]
            if change > 0:
                gains += change
            else:
                losses += abs(change)
                
        if losses == 0:
            return 100.0
        
        rs = (gains / 14) / (losses / 14)
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)

    def process_market_order(self, action, qty):
        executed_qty = 0
        avg_price = 0.0
        total_cost = 0.0
        
        if action == "BUY":
            sorted_asks = sorted(self.asks.keys())
            for price in sorted_asks:
                available = self.asks[price]
                if available == 0: continue
                
                fill_qty = min(qty - executed_qty, available)
                self.asks[price] -= fill_qty
                executed_qty += fill_qty
                total_cost += (fill_qty * price)
                
                if self.asks[price] == 0:
                    del self.asks[price]
                    
                if executed_qty >= qty:
                    break
        elif action == "SELL":
            sorted_bids = sorted(self.bids.keys(), reverse=True)
            for price in sorted_bids:
                available = self.bids[price]
                if available == 0: continue
                
                fill_qty = min(qty - executed_qty, available)
                self.bids[price] -= fill_qty
                executed_qty += fill_qty
                total_cost += (fill_qty * price)
                
                if self.bids[price] == 0:
                    del self.bids[price]
                    
                if executed_qty >= qty:
                    break
                    
        if executed_qty > 0:
            avg_price = total_cost / executed_qty
            self.current_price = avg_price
            self.price_history.append(self.current_price)
            if len(self.price_history) > 100: # Keep memory clean
                self.price_history.pop(0)
                
        return executed_qty, round(avg_price, 2)

    def generate_lob_state(self):
        # Sort and format top 5 levels for the payload
        top_bids = sorted([[p, q] for p, q in self.bids.items() if q > 0], key=lambda x: x[0], reverse=True)[:5]
        top_asks = sorted([[p, q] for p, q in self.asks.items() if q > 0], key=lambda x: x[0])[:5]
        
        # Inject Brownian Noise to OFI based on volume
        volatility_scale = max(1.0, self.recent_volume / 10000.0)
        brownian_noise = random.gauss(0, 0.05) * volatility_scale
        base_ofi = random.uniform(-0.3, 0.3)
        synthetic_ofi = max(-1.0, min(1.0, base_ofi + brownian_noise))

        # Add dummy liquidity if book is empty to prevent crashes
        if not top_bids: top_bids = [[self.current_price - 0.1, 1000]]
        if not top_asks: top_asks = [[self.current_price + 0.1, 1000]]

        return {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "asset_id": 1,
            "current_price": self.current_price,
            "mid_price": self.current_price,
            "vwap": self.current_price,
            "rsi": self.calculate_rsi(), # FIXED: RSI IS NOW CALCULATED
            "step_volume": int(self.recent_volume),
            "lob_asks": top_asks,
            "lob_bids": top_bids,
            "order_flow_imbalance": round(synthetic_ofi, 3)
        }

def run_true_engine():
    context = zmq.Context()
    host = os.getenv("ZMQ_HOST", "127.0.0.1")
    port = os.getenv("ZMQ_ORDER_PORT", "5555")

    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://{host}:{port}")

    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    logging.info(f"TRUE Matching Engine Online at {host}:{port}. Waiting for Swarm...")

    engine = MatchingEngine()
    total_requests = 0
    start_time = time.time()

    try:
        while True:
            socks = dict(poller.poll(timeout=50))

            if socket in socks and socks[socket] == zmq.POLLIN:
                message = socket.recv_json()

                if message.get("action") == "FETCH_STATE":
                    socket.send_json(engine.generate_lob_state())
                    total_requests += 1
                
                else:
                    action = message.get("action")
                    order_type = message.get("type", "MARKET")
                    qty = message.get("qty", 0)
                    price = message.get("price", engine.current_price)
                    
                    if order_type == "LIMIT":
                        engine.add_order(action, price, qty)
                        socket.send_json({"status": "ACKNOWLEDGED", "executed_qty": 0, "average_price": 0})
                    else: # MARKET ORDER (from Oracle or Retail)
                        executed_qty, avg_price = engine.process_market_order(action, qty)
                        engine.recent_volume = max(5000.0, (engine.recent_volume * 0.9) + (executed_qty * 0.1))
                        
                        socket.send_json({
                            "status": "FILLED" if executed_qty == qty else "PARTIAL",
                            "executed_qty": executed_qty,
                            "average_price": avg_price
                        })
                    total_requests += 1

            elapsed = time.time() - start_time
            if elapsed >= 1.0:
                if total_requests > 0:
                    logging.info(f"Processed {total_requests} Network Round-Trips per second. Vol: {int(engine.recent_volume)}")
                total_requests = 0
                start_time = time.time()

    except KeyboardInterrupt:
        logging.info("Shutting down true engine.")
        socket.close()
        context.term()

if __name__ == "__main__":
    run_true_engine()