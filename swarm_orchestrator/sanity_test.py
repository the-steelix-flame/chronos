# sanity_test.py
import pandas as pd
import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
from agents.agents import SmartMoneyEnv
from agents.backtest_retail import HeuristicRetailSwarm

print("\n--- CHRONOS AI INTEGRATION: SANITY CHECK ---\n")

print("1. Creating dummy market data...")
dummy_df = pd.DataFrame({
    'date': ['2026-01-01']*10, 
    'time': ['09:30:00']*10,
    'Open': [100]*10, 
    'High': [100]*10, 
    'Low': [100]*10, 
    'Close': [100]*10,
    'Volume': [1000]*10, 
    'VWAP': [100]*10, 
    'Volume_MA': [1000]*10,
    'Order_Flow_Imbalance': [0]*10, 
    'RSI_14': [50]*10
})

print("2. Loading Environment and Normalizers...")
# Instantiate the wrapper with a test max_capacity
raw_env = DummyVecEnv([lambda: SmartMoneyEnv(dummy_df, max_capacity=5000)])

# Load the running stats and lock them (CRITICAL: Do not let them update during inference)
try:
    norm_env = VecNormalize.load("agents/ml_models/mm_vec_normalize_stats.pkl", raw_env)
    norm_env.training = False
    norm_env.norm_reward = False
    print("   [OK] Normalizer loaded successfully.")
except Exception as e:
    print(f"   [ERROR] Failed to load Normalizer: {e}")

print("3. Loading Market Maker AI...")
try:
    model = PPO.load("agents/ml_models/market_maker_us_base.zip")
    print("   [OK] Neural Network loaded successfully.")
except Exception as e:
    print(f"   [ERROR] Failed to load Neural Network: {e}")

print("4. Testing an Inference Step...")
# Mock observation: [vwap_dist, vol, vol_ratio, rsi_norm, ofi, pos_norm]
raw_obs = np.array([[0.01, 0.002, 1.2, 0.55, 0.3, 0.0]], dtype=np.float32)

try:
    normalized_obs = norm_env.normalize_obs(raw_obs)
    action, _state = model.predict(normalized_obs, deterministic=True)
    print(f"\nSUCCESS! AI Output (Target Inventory %): {action[0][0]:.4f}")
    print("\nIf you see a float between -1.0 and 1.0 above, the handoff is complete. You are ready to build the engine.")
except Exception as e:
    print(f"   [ERROR] Inference failed: {e}")