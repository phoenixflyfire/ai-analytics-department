# ==========================================================
# ai_analytics_department/agents/business_analyst.py
# ==========================================================

from typing import Dict
from ai_analytics_department.tools.visualization import create_saleprice_distribution, create_correlation_chart
from ai_analytics_department.tools.reporting import generate_report, save_report_as_pdf
import litellm
from google.adk.agents import Agent
from ai_analytics_department.config.model_config import BUSINESS_ANALYST_MODEL, PROVIDER
from ai_analytics_department.utils.model_client import create_lite_llm
from ai_analytics_department.skills import create_business_analyst_toolset
from ai_analytics_department.config.agent_planner import get_planner

custom_model_key = f"gemini/{BUSINESS_ANALYST_MODEL}" if "gemini" not in BUSINESS_ANALYST_MODEL.lower() else BUSINESS_ANALYST_MODEL
litellm.model_cost[custom_model_key] = {
    "max_tokens": 8192,
    "input_cost_per_token": 0.00000025,
    "output_cost_per_token": 0.00000075,
    "litellm_provider": "gemini",
    "mode": "chat"
}

business_client = create_lite_llm(
    model=BUSINESS_ANALYST_MODEL,
    provider=PROVIDER,
    timeout=1200.0
)

business_analyst = Agent(
    name="business_analyst",
    mode="single_turn",
    include_contents="default",
    model=business_client,
    description="You are a Business Analyst responsible for converting data science models into strategic stakeholder value.",
    instruction="Use the business-reporting skill. Create charts and save the report as PDF. Mention saved file paths.",
    tools=[create_business_analyst_toolset(), create_saleprice_distribution, create_correlation_chart, save_report_as_pdf],
    planner=get_planner(),
    input_schema=None,
    output_schema=None
)
