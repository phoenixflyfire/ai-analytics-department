# ==========================================================
# MAIN ENTRY POINT: ai_analytics_department.agent
# ==========================================================

from ai_analytics_department.workflows.graph_workflow import compiled_workflow
from ai_analytics_department.logs.logfile import setup_logging
import litellm

setup_logging()
litellm._turn_on_debug()

# The ADK engine looks explicitly for 'root_agent' to kick off 'adk run'
root_agent = compiled_workflow
