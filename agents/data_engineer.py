# agents/data_engineer.py


from google.adk.agents import Agent
from ai_analytics_department.schemas.schemas import RawData, AdapterInput, DataEngineerStatus
from ai_analytics_department.config.model_config import ENGINEER_MODEL
from ai_analytics_department.config.model_config import PROVIDER
# from ai_analytics_department.config.model_config import BASE_URL  # enable for Gemini
from ai_analytics_department.utils.model_client import create_lite_llm
from ai_analytics_department.skills import create_data_engineer_toolset
from ai_analytics_department.tools.data_loader import load_dataset
from ai_analytics_department.config.agent_planner import get_planner
from google.genai import types

# Define the strict response schema for Gemini to enforce JSON mode.
generation_config = types.GenerateContentConfig(
    response_mime_type="application/json",
    response_schema=DataEngineerStatus,
)

engineer_client = create_lite_llm(
    model=ENGINEER_MODEL,
    provider=PROVIDER,
    timeout=1200.0,
)
# 2. Pass those initialized objects into your explicit agent setups
data_engineer = Agent(
    name="data_engineer",
    mode="single_turn",
    include_contents="default",
    model=engineer_client,
    description="You are a Data Engineer. Your only job is to load a dataset.",
    instruction="Your ONLY job is to load the dataset using the data-engineering skill. Call load_dataset(file_path) once, then output: {\"status\": \"tool_called\"}. Do NOT attempt EDA, modeling, charting, or reporting - those are handled by other agents in the pipeline.",
    tools=[create_data_engineer_toolset(), load_dataset],
    planner=get_planner(),
    input_schema=AdapterInput,
    output_schema=None
)