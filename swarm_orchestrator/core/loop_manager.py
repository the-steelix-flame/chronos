import asyncio
import random
import logging
from core.engine_client import EngineClient
from agents.live_agents import LiveRetailAgent # Needed for respawning

class SwarmOrchestrator:
    def __init__(self):
        self.client = EngineClient()
        self.agents = [] 
        self.running = False
        self.news_event_active = False # Will be triggered by Gemini Oracle later
        
    def load_agents(self, agents_list):
        self.agents = agents_list

    def enforce_dynamic_participation(self):
        """PDF Spec: Sleep/wake cycles. 30% active quiet, 100% active on news."""
        active_ratio = 1.0 if self.news_event_active else 0.30
        for agent in self.agents:
            agent.is_asleep = random.random() > active_ratio

    def enforce_retail_liquidation(self):
        """PDF Spec: Liquidate retail < $1000 and respawn."""
        for i, agent in enumerate(self.agents):
            if isinstance(agent, LiveRetailAgent):
                if agent.cash < 1000:
                    logging.info(f"Liquidating {agent.agent_id} (Cash: ${agent.cash:.2f}). Respawning.")
                    # Respawn with fresh capital as per PDF
                    self.agents[i] = LiveRetailAgent(agent.agent_id)

    async def run(self):
        self.running = True
        print(f"Swarm online. {len(self.agents)} agents pulling Notice Board data...")

        while self.running:
            # Enforce ecosystem rules before polling
            self.enforce_dynamic_participation()
            self.enforce_retail_liquidation()

            tick_data = await self.client.fetch_state()
            current_volume = tick_data.get("step_volume", 0)
            self.news_event_active = current_volume > 30000
            orders_to_send = []
            
            for agent in self.agents:
                new_orders = agent.on_price_update(tick_data)
                if new_orders:
                    orders_to_send.extend(new_orders)
            
            for order in orders_to_send:
                engine_reply = await self.client.send_order(order)
            
            await asyncio.sleep(0.001) 

    def shutdown(self):
        self.running = False
        self.client.shutdown()