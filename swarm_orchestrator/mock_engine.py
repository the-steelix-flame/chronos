import zmq
import json
import time
import random
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [ENGINE] - %(message)s')

def generate_lob_state(current_price):
    """Generates the Level 2 Limit Order Book payload."""
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "asset_id": 1,
        "current_price": round(current_price, 2), # Kept temporarily for your dummy agents
        "mid_price": round(current_price, 2),
        "vwap": round(current_price + random.uniform(-0.5, 0.5), 2),
        "step_volume": random.randint(10000, 50000),
        "lob_asks": [
            [round(current_price + 0.10, 2), random.randint(1000, 5000)],
            [round(current_price + 0.20, 2), random.randint(2000, 6000)]
        ],
        "lob_bids": [
            [round(current_price - 0.10, 2), random.randint(1000, 5000)],
            [round(current_price - 0.20, 2), random.randint(2000, 6000)]
        ],
        "sentiment": round(random.uniform(-1.0, 1.0), 2)
    }

def run_mock_engine():
    context = zmq.Context()
    host = os.getenv("ZMQ_HOST", "127.0.0.1")
    port = os.getenv("ZMQ_ORDER_PORT", "5555") # We now only use ONE port!

    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://{host}:{port}")

    # The 50ms Deadlock Fix
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)

    logging.info(f"Notice Board Engine Online at {host}:{port}. Waiting for Swarm...")

    current_price = 2500.50
    total_requests = 0
    start_time = time.time()

    try:
        while True:
            # Poll with a 50ms timeout. If an agent crashes, the engine doesn't freeze.
            socks = dict(poller.poll(timeout=50))

            if socket in socks and socks[socket] == zmq.POLLIN:
                message = socket.recv_json()

                # If Swarm wants data, give LOB state
                if message.get("action") == "FETCH_STATE":
                    current_price += random.uniform(-0.5, 0.5)
                    socket.send_json(generate_lob_state(current_price))
                    total_requests += 1
                
                # If Swarm sends an order, simulate Partial Fills
                else:
                    requested_qty = message.get("qty", 0)
                    executed_qty = int(requested_qty * random.uniform(0.8, 1.0)) # Simulate Volume Wall slippage
                    
                    socket.send_json({
                        "status": "FILLED" if executed_qty == requested_qty else "PARTIAL",
                        "executed_qty": executed_qty,
                        "average_price": round(current_price, 2)
                    })
                    total_requests += 1

            # Performance Metrics
            elapsed = time.time() - start_time
            if elapsed >= 1.0:
                if total_requests > 0:
                    logging.info(f"Processed {total_requests} Network Round-Trips per second.")
                total_requests = 0
                start_time = time.time()

    except KeyboardInterrupt:
        logging.info("Shutting down engine.")
        socket.close()
        context.term()

if __name__ == "__main__":
    run_mock_engine()