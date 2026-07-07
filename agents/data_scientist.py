# ==========================================================
# agents/data_scientist.py
# ==========================================================

import litellm
from google.adk.agents import Agent
from ai_analytics_department.config.model_config import SCIENTIST_MODEL, PROVIDER
from ai_analytics_department.utils.model_client import create_lite_llm
from ai_analytics_department.skills import create_data_scientist_toolset
from ai_analytics_department.tools.modeling import train_house_price_model
from ai_analytics_department.config.agent_planner import get_planner

custom_model_key = f"gemini/{SCIENTIST_MODEL}" if "gemini" not in SCIENTIST_MODEL.lower() else SCIENTIST_MODEL
litellm.model_cost[custom_model_key] = {
    "max_tokens": 8192,
    "input_cost_per_token": 0.00000025,
    "output_cost_per_token": 0.00000075,
    "litellm_provider": "gemini",
    "mode": "chat"
}

scientist_client = create_lite_llm(
    model=SCIENTIST_MODEL,
    provider=PROVIDER,
    timeout=1200.0
)

data_scientist = Agent(
    name="data_scientist",
    mode="single_turn",  
    model=scientist_client,
    include_contents="default",
    description="You are a Data Scientist responsible for building machine learning models.",
    instruction="Use the modeling skill. Call train_house_price_model() once (optionally passing target_column=<name>), then summarize the results. Do NOT attempt EDA, charting, or reporting.",
    tools=[create_data_scientist_toolset(), train_house_price_model],
    planner=get_planner(),
    input_schema=None, 
    output_schema=None         
)
