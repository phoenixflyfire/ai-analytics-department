# ================================================================
# workflows/graph_workflow.py
# ================================================================
import re
from typing import Any
from google.adk import Workflow, Event

from ai_analytics_department.agents.data_engineer import data_engineer
from ai_analytics_department.agents.analytics_manager import analytics_manager
from ai_analytics_department.agents.data_analyst import data_analyst
from ai_analytics_department.agents.data_scientist import data_scientist
from ai_analytics_department.agents.business_analyst import business_analyst
from ai_analytics_department.agents.senior_analytics_manager import senior_analytics_manager
from ai_analytics_department.workflows.router import manager_decision_router
from ai_analytics_department.tools.eda import engineer_output_adapter
from ai_analytics_department.tools.reporting import business_input_adapter

# ── Entry Gate ──────────────────────────────────────────────────
_ENTRY_CSV_RE = re.compile(
    r'((?:/[a-zA-Z0-9._/-]+|[a-zA-Z0-9._][a-zA-Z0-9._/-]*)\.csv)'
)


def _get_latest_user_text(ctx: Any) -> str:
    events = (
        getattr(ctx, "events", [])
        or getattr(getattr(ctx, "session", None), "events", [])
    )
    for raw_event in reversed(events):
        event = raw_event
        if isinstance(event, dict) and event.get("author") == "user":
            content = event.get("content") or {}
            parts = content.get("parts", [])
            return "".join(
                str(p.get("text", "")) for p in parts
                if isinstance(p, dict) and not p.get("thought")
            )
    return ""


def _has_csv_path(text: str) -> bool:
    return bool(_ENTRY_CSV_RE.search(text.lower()))


def entry_gate(ctx: Any) -> Event:
    from ai_analytics_department.schemas.shared_data import data_container as _dc
    if not _dc.pipeline_complete:
        return Event(route="analytics_manager", output={})
    user_text = _get_latest_user_text(ctx)
    if _has_csv_path(user_text):
        _dc.pipeline_complete = False
        _dc.current_csv_path = None
        return Event(route="analytics_manager", output={})
    return Event(route="senior_analytics_manager", output={})


ENTRY_ROUTING_MAP = {
    "analytics_manager": analytics_manager,
    "senior_analytics_manager": senior_analytics_manager,
}

# ── Spoke Routing Map ───────────────────────────────────────────
SPOKE_ROUTING_MAP = {
    "data_engineer":    data_engineer,
    "data_analyst":     data_analyst,
    "data_scientist":   data_scientist,
    "business_analyst": business_analyst,
    "senior_analytics_manager": senior_analytics_manager,
}

# ==========================================================
# STAR TOPOLOGY WORKFLOW
# analytics_manager is the central hub.
# Every spoke agent routes back to the hub after completing.
# The hub router (manager_decision_router) decides which
# spoke to activate next based on session history.
# ==========================================================
compiled_workflow = Workflow(
    name="ai_analytics_department_workflow",
    edges=[
        # Entry point: entry_gate routes to analytics_manager or senior
        ("START", entry_gate, ENTRY_ROUTING_MAP),

        # Hub → router selects which spoke to activate next
        (analytics_manager, manager_decision_router, SPOKE_ROUTING_MAP),

        # Spoke 1: Data Engineer → adapter → back to hub
        (data_engineer, engineer_output_adapter),
        (engineer_output_adapter, analytics_manager),

        # Spoke 2: Data Analyst → back to hub
        (data_analyst, analytics_manager),

        # Spoke 3: Data Scientist → presentation adapter → back to hub
        (data_scientist, business_input_adapter),
        (business_input_adapter, analytics_manager),

        # Spoke 4: Business Analyst → back to hub
        (business_analyst, analytics_manager),

        # Spoke 5: Senior Analytics Manager → back to router (post-pipeline Q&A)
        # Directly to router, NOT analytics_manager, to prevent infinite loop
        # where analytics_manager treats senior's output as new input.
        (senior_analytics_manager, manager_decision_router),
    ]
)
