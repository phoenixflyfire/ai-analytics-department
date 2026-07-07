import os
import sys
from pathlib import Path
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioConnectionParams
from mcp.client.stdio import StdioServerParameters
from ai_analytics_department.config.model_config import MANAGER_MODEL
from ai_analytics_department.config.model_config import PROVIDER
from ai_analytics_department.utils.model_client import create_lite_llm
from ai_analytics_department.tools.data_query import get_schema, query_df
from ai_analytics_department.config.agent_planner import get_planner

senior_client = create_lite_llm(
    model=MANAGER_MODEL,
    provider=PROVIDER,
    timeout=1200.0,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_mcp_env = os.environ.copy()
_mcp_env["PYTHONPATH"] = str(PROJECT_ROOT) + ":" + _mcp_env.get("PYTHONPATH", "")

mcp_csv_tools = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_server.server"],
            env=_mcp_env,
            cwd=str(PROJECT_ROOT),
        ),
        timeout=30,
    ),
    tool_name_prefix="mcp_",
)

senior_analytics_manager = Agent(
    name="senior_analytics_manager",
    mode="single_turn",
    model=senior_client,
    include_contents="default",
    description="Senior Analytics Manager for post-pipeline Q&A.",
    instruction="""
    The data pipeline has completed. Answer questions using the conversation history and the available tools.
    You have direct tools (get_schema, query_df) for the pipeline's loaded data, and MCP tools (mcp_load_csv, mcp_get_schema, mcp_query_csv) for analyzing any CSV file by path.

    After the pipeline completes, proactively offer to compare the training data against a test CSV.
    Say something like: "Would you like me to compare this training data against a test CSV (e.g. test.csv)
    to see how well the model might perform on new data? Just tell me the file name or provide the full path."
    This helps novices understand that the trained model should be evaluated against unseen data.

    Also proactively offer Cloud Run deployment. Say something like:
    "A Cloud Engineer would handle production deployment. This application includes an MCP tool (mcp_deploy_to_cloud_run) that automates the process. The prerequisites are:
    - A GCP project with billing enabled
    - Cloud Run API, Cloud Build API, and Artifact Registry API enabled
    - Application Default Credentials configured (gcloud auth application-default login)
    - GEMINI_API_KEY provided
    If these conditions are met, the available tools can deploy this application by providing your GCP Project ID."

    If the user provides a CSV path in the context of comparing datasets, use mcp_compare_datasets(path_a, path_b)
    where path_a is the training file loaded in the pipeline and path_b is the user's test CSV.
    This will show structural differences (rows, columns, schema, missing values, type mismatches, statistics).

    If the user clearly wants a new full pipeline run (e.g. a completely different dataset), say "Processing new file..."
    and the pipeline will restart.

    Use get_schema() and query_df() to answer questions about the loaded data.
    Use mcp_load_csv(file_path) first to load a CSV via MCP, then mcp_query_csv() to analyze it.
    You also have mcp_compare_datasets(path_a, path_b) to compare two CSV files side-by-side (rows, schema, missing values, distributions).
    """,
    tools=[get_schema, query_df, mcp_csv_tools],
    planner=get_planner(),
    input_schema=None,
    output_schema=None,
)
