import asyncio
import pandas as pd
import sys
from core.loop_manager import SwarmOrchestrator
from agents.dummy_classes import MarketMakerAgent, HedgeFundAgent, MomentumAgent, HistoricalReplayer

async def main():
    orchestrator = SwarmOrchestrator()
    swarm = []

    # 1. Instantiate 15 Market Makers
    for i in range(15):
        swarm.append(MarketMakerAgent(f"MM_{i}"))

    # 2. Instantiate 4 Hedge Funds
    for i in range(4):
        swarm.append(HedgeFundAgent(f"HF_{i}"))

    # 3. Instantiate 80 Momentum Agents
    for i in range(80):
        swarm.append(MomentumAgent(f"MOM_{i}"))

    # 4. Instantiate 1 Historical Replayer (Requires a dummy DataFrame for now)
    dummy_df = pd.DataFrame({'Close': [100.0] * 1000}) 
    swarm.append(HistoricalReplayer("GHOST_01", dummy_df))

    # Load and run
# ... [Keep your agent setup the same] ...
    
    orchestrator.load_agents(swarm)
    
    try:
        await orchestrator.run()
    except asyncio.CancelledError:
        pass # Silently catch the async cancellation
    except KeyboardInterrupt:
        pass
    finally:
        logging.info("Shutting down swarm orchestrator...")
        orchestrator.shutdown()

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass 