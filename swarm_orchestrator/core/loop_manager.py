import asyncio
from core.engine_client import EngineClient

class SwarmOrchestrator:
    def __init__(self):
        self.client = EngineClient()
        self.agents = [] 
        
    def load_agents(self, agents_list):
        """Loads the instantiated agents into the swarm."""
        self.agents = agents_list

    async def process_tick(self, tick_data):
        """
        Distributes the tick to all agents, collects orders, and fires them.
        """
        orders_to_send = []
        
        # 1. Synchronous math loop (micro-seconds for 100 agents, highly optimized)
        for agent in self.agents:
            new_orders = agent.on_price_update(tick_data)
            if new_orders:
                orders_to_send.extend(new_orders)
        
        # 2. Fire-and-forget all orders concurrently to ZeroMQ
        if orders_to_send:
            send_tasks = [self.client.send_order(order) for order in orders_to_send]
            await asyncio.gather(*send_tasks)

    async def run(self):
        """Starts the swarm."""
        print(f"Swarm online. {len(self.agents)} agents listening for ticks...")
        await self.client.listen_for_ticks(self.process_tick)

    def shutdown(self):
        self.client.shutdown()