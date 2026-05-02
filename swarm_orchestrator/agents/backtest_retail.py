import pandas as pd
import numpy as np
from stable_baselines3.common.vec_env import DummyVecEnv
from agents.agents import SmartMoneyEnv

class HeuristicRetailSwarm:
    """
    A hardcoded, rule-based agent that simulates the chaotic, 
    emotional trading of a retail crowd. Zero training required.
    """
    def predict(self, obs, deterministic=True):
        # DummyVecEnv wraps obs in an extra array, so we grab index 0
        obs_data = obs[0] 
        
        # Unpack the normalized observations from your UniversalMarketEnv
        vwap_dist = obs_data[0]
        volatility = obs_data[1]
        volume_ratio = obs_data[2]
        rsi_norm = obs_data[3]  # 0.0 to 1.0 (50 RSI = 0.5)
        ofi = obs_data[4]       # Order Flow Imbalance (-1.0 to 1.0)
        
        action = 0.0 # Default to flat

        # Rule 1: The Basic Technical Analyst (Buy oversold, sell overbought)
        if rsi_norm < 0.30:
            action = 0.5   # Buy with 50% capacity
        elif rsi_norm > 0.70:
            action = -0.5  # Short with 50% capacity

        # Rule 2: The FOMO & Panic Traders (Overrides RSI)
        # If order flow is extremely toxic one way, retail piles in emotionally
        if ofi > 0.8:
            action = 0.8   # Aggressive FOMO Buy
        elif ofi < -0.8:
            action = -1.0  # Absolute Panic Sell

        # Rule 3: Pure Noise (10% of the time, the swarm does something random)
        if np.random.rand() < 0.10:
            action = np.random.uniform(-0.5, 0.5)

        return np.array([[action]]), None

def main():
    print("Loading Processed Data...")
    df = pd.read_csv("data/processed_spy_1min.csv")
    
    unique_dates = sorted(df['date'].unique())
    split_idx = int(len(unique_dates) * 0.8)
    test_dates = unique_dates[split_idx:]
    test_df = df[df['date'].isin(test_dates)].copy()

    print(f"\n{'='*50}\nEvaluating: The Retail Swarm (Rule-Based)\n{'='*50}")
    
    # We use the SmartMoneyEnv because the Retail Swarm is also a directional trader,
    # but we cap their capacity at 2,000 shares to simulate a smaller account size.
    test_env = DummyVecEnv([lambda: SmartMoneyEnv(test_df, max_capacity=2000)])
    
    # Load our hardcoded rule-based brain
    model = HeuristicRetailSwarm()
    
    # FIX: DummyVecEnv doesn't use the .venv attribute
    underlying_env = test_env.envs[0]
    safe_test_dates = sorted(underlying_env.unique_dates)
    
    total_pnl = 0
    
    for day_idx, test_date in enumerate(safe_test_dates):
        underlying_env.unique_dates = [test_date] 
        obs = test_env.reset()
        
        done = False
        while not done:
            action, _ = model.predict(obs)
            obs, reward, done_array, info_list = test_env.step(action)
            done = done_array[0]
            
            if done:
                final_info = info_list[0]
                day_pnl = final_info['portfolio_value'] - underlying_env.initial_capital
                total_pnl += day_pnl
                
                print(f"Day {day_idx+1:03d} | Date: {test_date} | PnL: ${day_pnl:>8,.2f} | End Position: {final_info['position']:>5}")

    print(f"\n>>> FINAL RETAIL SWARM TEST PNL: ${total_pnl:,.2f} <<<\n")
    print("Note: A negative PnL here is ACTUALLY GOOD. The swarm is supposed to lose money to the Market Maker!")

if __name__ == "__main__":
    main()