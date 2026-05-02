import asyncio
from core.engine_client import EngineClient

class SwarmOrchestrator:
    def __init__(self):
        self.client = EngineClient()
        self.agents = [] 
        self.running = False
        
    def load_agents(self, agents_list):
        self.agents = agents_list

    async def run(self):
        self.running = True
        print(f"Swarm online. {len(self.agents)} agents pulling Notice Board data...")

        while self.running:
            # 1. PULL the data (Notice Board Architecture)
            tick_data = await self.client.fetch_state()
            
            orders_to_send = []
            
            # 2. Agents process the state
            for agent in self.agents:
                new_orders = agent.on_price_update(tick_data)
                if new_orders:
                    orders_to_send.extend(new_orders)
            
            # 3. Send orders sequentially (REQ sockets require Send->Wait->Receive flow)
            for order in orders_to_send:
                engine_reply = await self.client.send_order(order)
                # Later, the ML models will read engine_reply to update their inventory.
            
            # Yield control to prevent Python from freezing your CPU at 100%
            await asyncio.sleep(0.001) 

    def shutdown(self):
        self.running = False
        self.client.shutdown()