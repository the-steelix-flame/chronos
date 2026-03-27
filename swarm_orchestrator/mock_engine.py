import zmq
import json
import time
import random
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [ENGINE] - %(message)s')

def run_stress_test():
    context = zmq.Context()
    
    host = os.getenv("ZMQ_HOST", "127.0.0.1")
    order_port = os.getenv("ZMQ_ORDER_PORT", "5555")
    tick_port = os.getenv("ZMQ_TICK_PORT", "5556")
    
    pub_socket = context.socket(zmq.PUB)
    pub_socket.bind(f"tcp://{host}:{tick_port}")
    
    sub_socket = context.socket(zmq.SUB)
    sub_socket.bind(f"tcp://{host}:{order_port}")
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, "ORDER_QUEUE")
    
    logging.info("Stress Test Engine Online. Waiting 2 seconds...")
    time.sleep(2)
    
    current_price = 100.0
    total_orders_received = 0
    start_time = time.time()
    
    try:
        logging.info("Initiating high-speed tick broadcast...")
        while True:
            current_price += random.uniform(-0.5, 0.5)
            tick_payload = {"current_price": round(current_price, 2)}
            pub_socket.send_string(f"TICK_DATA {json.dumps(tick_payload)}")
            
            try:
                while True:
                    sub_socket.recv_string(flags=zmq.NOBLOCK)
                    total_orders_received += 1
            except zmq.Again:
                pass 
                
            elapsed = time.time() - start_time
            if elapsed >= 1.0:
                logging.info(f"Processed {total_orders_received} orders per second.")
                total_orders_received = 0
                start_time = time.time()
                
    except KeyboardInterrupt:
        logging.info("Ending stress test.")
        pub_socket.close()
        sub_socket.close()
        context.term()

if __name__ == "__main__":
    run_stress_test()