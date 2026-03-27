import asyncio
import zmq
import zmq.asyncio
import json
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure professional logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - [SWARM] - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("swarm.log"), logging.StreamHandler()]
)

class EngineClient:
    def __init__(self):
        """Initializes async ZeroMQ sockets using .env configuration."""
        self.context = zmq.asyncio.Context()
        
        host = os.getenv("ZMQ_HOST", "127.0.0.1")
        order_port = os.getenv("ZMQ_ORDER_PORT", "5555")
        tick_port = os.getenv("ZMQ_TICK_PORT", "5556")
        
        self.pub_socket = self.context.socket(zmq.PUB)
        self.pub_socket.connect(f"tcp://{host}:{order_port}")
        
        self.sub_socket = self.context.socket(zmq.SUB)
        self.sub_socket.connect(f"tcp://{host}:{tick_port}")
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "TICK_DATA")
        
        logging.info(f"Connected to Engine at {host} (PUB:{order_port}, SUB:{tick_port})")

    async def send_order(self, order_dict: dict):
        payload = json.dumps(order_dict)
        await self.pub_socket.send_string(f"ORDER_QUEUE {payload}")

    async def listen_for_ticks(self, callback_func):
        while True:
            message = await self.sub_socket.recv_string()
            topic, data_str = message.split(" ", 1)
            tick_data = json.loads(data_str)
            asyncio.create_task(callback_func(tick_data))
            
    def shutdown(self):
        logging.info("Shutting down ZeroMQ connections...")
        self.pub_socket.close()
        self.sub_socket.close()
        self.context.term()