# ==========================================================
# tests/test_star_topology.py
# Pytest suite for the Star Topology refactoring validation
# ==========================================================
import os
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch
from ai_analytics_department.workflows.router import manager_decision_router
from ai_analytics_department.workflows.router import universal_deserialize
from ai_analytics_department.workflows.router import _diag_off


# Silence diagnostic logs during tests
_diag_off()


# --- Helpers ---

def make_event(author: str, text: str) -> dict:
    return {
        "author": author,
        "content": {"parts": [{"text": text}]},
    }

def make_approval_event(author: str, text: str, fc_name: str | None = None) -> dict:
    parts = [{"text": text}]
    if fc_name:
        parts.append({"function_call": {"name": fc_name, "args": {"file_path": "/data/raw/train.csv"}}})
    return {"author": author, "content": {"parts": parts}}

def make_ctx(events: list) -> MagicMock:
    ctx = MagicMock()
    ctx.events = events
    return ctx

# --- Tests ---

def test_router_no_history_no_csv():
    ctx = make_ctx([])
    result = manager_decision_router(ctx)
    assert result.actions.route == "END"

def test_router_csv_without_approval_waits(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    ctx = make_ctx([make_event("user", "Please analyze /data/raw/train.csv")])
    result = manager_decision_router(ctx)
    assert result.actions.route == "END"

def test_router_csv_with_approval_routes_to_engineer(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    ctx = make_ctx([
        make_event("user", "Please analyze /data/raw/train.csv"),
        make_approval_event("analytics_manager", "Pipeline approved.", "request_pipeline_approval"),
    ])
    result = manager_decision_router(ctx)
    assert result.actions.route == "data_engineer"

def test_router_old_approval_ignored_when_latest_is_question(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    ctx = make_ctx([
        make_event("user", "Please analyze /data/raw/train.csv"),
        make_approval_event("analytics_manager", "Pipeline approved.", "request_pipeline_approval"),
        make_event("user", "analyze /data/other.csv"),
        make_event("analytics_manager", "Shall I proceed with the pipeline?"),
    ])
    result = manager_decision_router(ctx)
    assert result.actions.route == "END"

def test_router_after_engineer_routes_to_analyst():
    from ai_analytics_department.schemas.shared_data import data_container as _dc
    _dc.current_csv_path = None
    _dc.pipeline_complete = False
    ctx = make_ctx([make_event("data_engineer", "Data loaded.")])
    result = manager_decision_router(ctx)
    assert result.actions.route == "data_analyst"

def test_router_after_analyst_scientist_decision():
    payload = '{"next_step": "SCIENTIST"}'
    ctx = make_ctx([make_event("data_analyst", payload)])
    result = manager_decision_router(ctx)
    assert result.actions.route == "data_scientist"

def test_router_after_analyst_engineer_decision():
    payload = '{"next_step": "ENGINEER"}'
    ctx = make_ctx([make_event("data_analyst", payload)])
    result = manager_decision_router(ctx)
    assert result.actions.route == "data_engineer"

def test_router_after_scientist_routes_to_business_analyst():
    ctx = make_ctx([make_event("data_scientist", "Model metrics complete.")])
    result = manager_decision_router(ctx)
    assert result.actions.route == "business_analyst"

def test_router_after_business_analyst_routes_to_senior():
    ctx = make_ctx([make_event("business_analyst", "Executive report delivered.")])
    result = manager_decision_router(ctx)
    assert result.actions.route == "senior_analytics_manager"

def test_router_senior_no_csv_stays_on_senior():
    from ai_analytics_department.schemas.shared_data import data_container as _dc
    _dc.pipeline_complete = False
    ctx = make_ctx([make_event("senior_analytics_manager", "Ask me anything.")])
    result = manager_decision_router(ctx)
    assert result.actions.route == "senior_analytics_manager"

def test_router_senior_no_new_user_message_stays_in_qa():
    from ai_analytics_department.schemas.shared_data import data_container as _dc
    _dc.pipeline_complete = False
    ctx = make_ctx([
        make_event("senior_analytics_manager", "I am ready."),
        make_event("analytics_manager", "Understood."),
    ])
    result = manager_decision_router(ctx)
    assert result.actions.route == "senior_analytics_manager"

def test_router_senior_with_new_csv_after_pipeline_goes_to_end(monkeypatch):
    from ai_analytics_department.schemas.shared_data import data_container as _dc
    _dc.pipeline_complete = True
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    ctx = make_ctx([
        make_event("senior_analytics_manager", "Ask me anything."),
        make_event("user", "analyze /data/new.csv"),
    ])
    result = manager_decision_router(ctx)
    assert result.actions.route == "END"
    _dc.pipeline_complete = False

def test_router_pipeline_complete_no_spoke_routes_to_senior():
    from ai_analytics_department.schemas.shared_data import data_container as _dc
    _dc.pipeline_complete = True
    ctx = make_ctx([make_event("user", "tell me more")])
    result = manager_decision_router(ctx)
    assert result.actions.route == "senior_analytics_manager"
    _dc.pipeline_complete = False

def test_router_user_affirms_after_ask_routes_to_engineer(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    ctx = make_ctx([
        make_event("user", "Please analyze /data/raw/train.csv"),
        make_event("analytics_manager", "Shall I proceed with the pipeline?"),
        make_event("user", "yes"),
    ])
    result = manager_decision_router(ctx)
    assert result.actions.route == "data_engineer"

def test_router_pipeline_complete_new_csv_approval_restarts(monkeypatch):
    from ai_analytics_department.schemas.shared_data import data_container as _dc
    _dc.pipeline_complete = True
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    ctx = make_ctx([
        make_event("user", "analyze /data/train.csv"),
        make_event("analytics_manager", "Shall I proceed?"),
        make_event("user", "yes"),
    ])
    result = manager_decision_router(ctx)
    assert result.actions.route == "data_engineer"
    _dc.pipeline_complete = False

def test_router_pipeline_complete_senior_qa_new_csv_waits_for_approval(monkeypatch):
    from ai_analytics_department.schemas.shared_data import data_container as _dc
    _dc.pipeline_complete = True
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    ctx = make_ctx([
        make_event("business_analyst", "Report ready."),
        make_event("senior_analytics_manager", "Ask me anything."),
        make_event("user", "analyze /data/new.csv"),
    ])
    result = manager_decision_router(ctx)
    assert result.actions.route == "END"
    _dc.pipeline_complete = False

# --- Security validation tests ---

def test_validate_csv_path_allows_normal():
    from ai_analytics_department.workflows.router import _validate_csv_path
    assert _validate_csv_path("data/raw/train.csv") == "data/raw/train.csv"
    assert _validate_csv_path("/home/user/file.csv") == "/home/user/file.csv"


def test_validate_csv_path_rejects_traversal():
    from ai_analytics_department.workflows.router import _validate_csv_path
    assert _validate_csv_path("../etc/passwd.csv") is None
    assert _validate_csv_path("data/../../etc/passwd.csv") is None
    assert _validate_csv_path("~/data/file.csv") is None


def test_validate_csv_path_rejects_shell_meta():
    from ai_analytics_department.workflows.router import _validate_csv_path
    assert _validate_csv_path("data/raw/train.csv;rm") is None
    assert _validate_csv_path("data/raw/train.csv|cat") is None
    assert _validate_csv_path("$(cat /etc/passwd).csv") is None


def test_validate_csv_path_rejects_wrong_extension():
    from ai_analytics_department.workflows.router import _validate_csv_path
    assert _validate_csv_path("data/raw/train.xlsx") is None
    assert _validate_csv_path("data/raw/train.csv.exe") is None


# --- HITL tool tests ---

def test_hitl_approves_valid_path():
    from ai_analytics_department.tools.hitl import request_pipeline_approval
    result = request_pipeline_approval("data/raw/train.csv")
    assert result["status"] == "approved"
    assert result["file_path"] == "data/raw/train.csv"


def test_hitl_denies_empty_path():
    from ai_analytics_department.tools.hitl import request_pipeline_approval
    result = request_pipeline_approval("")
    assert result["status"] == "denied"


def test_hitl_tool_is_approval_gate():
    from ai_analytics_department.tools.hitl import approve_pipeline_tool
    assert approve_pipeline_tool is not None
    assert callable(approve_pipeline_tool.func)


# --- Infinite loop prevention tests ---

def test_router_pipeline_complete_same_csv_does_not_restart(monkeypatch):
    from ai_analytics_department.schemas.shared_data import data_container as _dc
    _dc.pipeline_complete = True
    _dc.current_csv_path = "/data/train.csv"
    _dc.pipeline_cycle = 1
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    ctx = make_ctx([
        make_event("user", "analyze /data/train.csv"),
        make_event("analytics_manager", "Shall I proceed?"),
        make_event("user", "yes"),
    ])
    result = manager_decision_router(ctx)
    assert result.actions.route != "data_engineer"
    _dc.pipeline_complete = False
    _dc.current_csv_path = None
    _dc.pipeline_cycle = 0


def test_router_new_csv_after_completion_restarts(monkeypatch):
    from ai_analytics_department.schemas.shared_data import data_container as _dc
    _dc.pipeline_complete = True
    _dc.current_csv_path = "/data/old.csv"
    _dc.pipeline_cycle = 1
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    ctx = make_ctx([
        make_event("user", "analyze /data/new.csv"),
        make_event("analytics_manager", "Shall I proceed?"),
        make_event("user", "yes"),
    ])
    result = manager_decision_router(ctx)
    assert result.actions.route == "data_engineer"
    _dc.pipeline_complete = False
    _dc.current_csv_path = None
    _dc.pipeline_cycle = 0


def test_router_duplicate_csv_path_dedup(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    ctx = make_ctx([
        make_event("user", "analyze /data/train.csv/data/train.csv"),
    ])
    from ai_analytics_department.workflows.router import _deduplicate_user_input
    assert _deduplicate_user_input("abcabc") == "abc"
    assert _deduplicate_user_input("hello") == "hello"
    assert _deduplicate_user_input("") == ""


# --- Generic EDA tests ---

def test_eda_no_data_returns_no_data():
    from ai_analytics_department.tools.eda import run_eda
    from ai_analytics_department.schemas.shared_data import data_container as _dc
    _dc.df = pd.DataFrame()
    result = run_eda()
    assert result["status"] == "NO_DATA"
    assert result["rows"] == 0


# --- Generic visualization tests ---

def test_create_saleprice_distribution_no_column_fallback():
    from ai_analytics_department.tools.visualization import create_saleprice_distribution
    from ai_analytics_department.schemas.shared_data import data_container as _dc
    import pandas as pd
    _dc.df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    result = create_saleprice_distribution()
    assert "chart" in result
    _dc.df = pd.DataFrame()


# --- Diagnostic logging tests ---

def test_diag_logs_router_entry(caplog):
    from ai_analytics_department.workflows.router import _reset_diag, _diag_off
    _reset_diag()
    caplog.set_level(10)
    ctx = make_ctx([make_event("user", "hello")])
    result = manager_decision_router(ctx)
    assert result.actions.route == "END"
    messages = [r.message for r in caplog.records]
    found_entry = any("ROUTER_ENTER" in m for m in messages)
    assert found_entry, f"Expected ROUTER_ENTER in logs. Got: {messages}"
    found_route = any("→ END" in m for m in messages)
    assert found_route, f"Expected route decision in logs. Got: {messages}"
    _diag_off()