import zmq
import time
import random
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [ENGINE] - %(message)s')

def generate_lob_state(current_price, recent_volume):
    """Generates Level 2 LOB with Dynamic Brownian Noise injected into OFI."""
    
    # PDF SPEC: Scale noise dynamically with overall market volume
    volatility_scale = max(1.0, recent_volume / 10000.0)
    
    # PDF SPEC: Inject a tiny amount of randomized synthetic volume (Brownian jitter)
    brownian_noise = random.gauss(0, 0.05) * volatility_scale
    
    # Apply noise to Order Flow Imbalance (bounded between -1.0 and 1.0)
    base_ofi = random.uniform(-0.3, 0.3)
    synthetic_ofi = max(-1.0, min(1.0, base_ofi + brownian_noise))
    
    # Apply microscopic jitter to the actual price
    jittered_price = current_price + (brownian_noise * 0.1)

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "asset_id": 1,
        "current_price": round(jittered_price, 2),
        "mid_price": round(jittered_price, 2),
        "vwap": round(jittered_price + random.uniform(-0.5, 0.5), 2),
        "step_volume": int(recent_volume),
        "lob_asks": [
            [round(jittered_price + 0.10, 2), random.randint(1000, 5000)],
            [round(jittered_price + 0.20, 2), random.randint(2000, 6000)]
        ],
        "lob_bids": [
            [round(jittered_price - 0.10, 2), random.randint(1000, 5000)],
            [round(jittered_price - 0.20, 2), random.randint(2000, 6000)]
        ],
        "order_flow_imbalance": round(synthetic_ofi, 3),
        "sentiment": round(random.uniform(-1.0, 1.0), 2)
    }

def run_mock_engine():
    context = zmq.Context()
    host = os.getenv("ZMQ_HOST", "127.0.0.1")
    port = os.getenv("ZMQ_ORDER_PORT", "5555")

    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://{host}:{port}")

    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    logging.info(f"Notice Board Engine Online at {host}:{port}. Waiting for Swarm...")

    current_price = 2500.50
    recent_volume = 10000.0 # Tracks dynamic market volume
    total_requests = 0
    start_time = time.time()

    try:
        while True:
            socks = dict(poller.poll(timeout=50))

            if socket in socks and socks[socket] == zmq.POLLIN:
                message = socket.recv_json()

                if message.get("action") == "FETCH_STATE":
                    socket.send_json(generate_lob_state(current_price, recent_volume))
                    total_requests += 1
                
                else:
                    # Parse Order
                    requested_qty = message.get("qty", 0)
                    executed_qty = int(requested_qty * random.uniform(0.8, 1.0))
                    
                    # Update dynamic volume tracker
                    recent_volume = max(5000.0, (recent_volume * 0.9) + (executed_qty * 0.1))
                    
                    # Real price impact mechanics
                    if message.get("action") == "BUY":
                        current_price += 0.005 * (executed_qty / 1000)
                    elif message.get("action") == "SELL":
                        current_price -= 0.005 * (executed_qty / 1000)
                        
                    socket.send_json({
                        "status": "FILLED" if executed_qty == requested_qty else "PARTIAL",
                        "executed_qty": executed_qty,
                        "average_price": round(current_price, 2)
                    })
                    total_requests += 1

            elapsed = time.time() - start_time
            if elapsed >= 1.0:
                if total_requests > 0:
                    logging.info(f"Processed {total_requests} Network Round-Trips per second. Vol: {int(recent_volume)}")
                total_requests = 0
                start_time = time.time()

    except KeyboardInterrupt:
        logging.info("Shutting down engine.")
        socket.close()
        context.term()

if __name__ == "__main__":
    run_mock_engine()