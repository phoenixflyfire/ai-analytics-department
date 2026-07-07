# ==========================================================
# agents/data_analyst.py
# ==========================================================

import litellm
import json
from google.adk.agents import Agent
from ai_analytics_department.schemas.schemas import RawData
from ai_analytics_department.config.model_config import ANALYST_MODEL
from ai_analytics_department.config.model_config import PROVIDER
from ai_analytics_department.utils.model_client import create_lite_llm
from ai_analytics_department.skills import create_data_analyst_toolset
from ai_analytics_department.tools.eda import run_eda
from ai_analytics_department.config.agent_planner import get_planner

# Patch the LiteLLM lookup tracking costs dictionary
custom_model_key = f"gemini/{ANALYST_MODEL}" if "gemini" not in ANALYST_MODEL.lower() else ANALYST_MODEL
litellm.model_cost[custom_model_key] = {
    "max_tokens": 8192,
    "input_cost_per_token": 0.00000025,
    "output_cost_per_token": 0.00000075,
    "litellm_provider": "gemini",
    "mode": "chat"
}

analyst_client = create_lite_llm(
    model=ANALYST_MODEL,
    provider=PROVIDER,
    timeout=1200.0
)

data_analyst = Agent(
    name="data_analyst",
    mode="single_turn",
    include_contents="default", 
    model=analyst_client,
    description="You are a Data Analyst responsible for performing EDA.",
    instruction="Use the data-analysis skill. Call run_eda() once, then output JSON: {\"summary\": \"...\", \"next_step\": \"SCIENTIST\"}.",
    tools=[create_data_analyst_toolset(), run_eda],
    planner=get_planner(),
    input_schema=RawData, 
    output_schema=None
)