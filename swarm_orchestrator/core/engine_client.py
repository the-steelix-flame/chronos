import asyncio
import zmq
import zmq.asyncio
import os
import logging
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [SWARM] - %(message)s')

class EngineClient:
    def __init__(self):
        """Initializes async ZeroMQ REQ socket for Notice Board architecture."""
        self.context = zmq.asyncio.Context()
        host = os.getenv("ZMQ_HOST", "127.0.0.1")
        port = os.getenv("ZMQ_ORDER_PORT", "5555")

        self.req_socket = self.context.socket(zmq.REQ)
        self.req_socket.connect(f"tcp://{host}:{port}")
        
        logging.info(f"Connected to Notice Board at {host}:{port}")

    async def fetch_state(self):
        """Pulls the latest Level 2 LOB state from the Engine."""
        await self.req_socket.send_json({"action": "FETCH_STATE"})
        return await self.req_socket.recv_json()

    async def send_order(self, order_dict: dict):
        """Sends an order and waits for the Engine's Partial Fill confirmation."""
        await self.req_socket.send_json(order_dict)
        return await self.req_socket.recv_json()

    def shutdown(self):
        self.req_socket.close()
        self.context.term()