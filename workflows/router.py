# ==========================================================
# ai_analytics_department/workflows/router.py
# ==========================================================

import json
import logging
from typing import Any
import os
import re
# IMPORT THE OFFICIAL ADK EVENT CLASS AS SPECIFIED BY PAGE 137:
from google.adk import Event

logger = logging.getLogger('google_adk.' + __name__)

_DIAG = True
"""Set False in tests to silence diagnostic logs."""

def _log(msg: str, *args: Any) -> None:
    if _DIAG:
        logger.info('[DIAG] ' + msg, *args)

def _reset_diag() -> None:
    global _DIAG
    _DIAG = True

def _diag_off() -> None:
    global _DIAG
    _DIAG = False

def _extract_event_dict(event: Any) -> dict:
    """
    Safely converts an ADK Event object or dictionary into a plain dict.
    Bypasses "'Event' object has no attribute 'get'" with strict type casting.
    """
    if isinstance(event, dict):
        return event
    if hasattr(event, "to_dict") and callable(getattr(event, "to_dict", None)):
        return event.to_dict()  # type: ignore
    if hasattr(event, "model_dump") and callable(getattr(event, "model_dump", None)):
        return event.model_dump()  # type: ignore
    if hasattr(event, "__dict__"):
        return event.__dict__  # type: ignore
    return {}

def _get_event_text(event: dict) -> str:
    content = event.get("content") or {}
    parts = content.get("parts", [])
    return "".join(
        str(p.get("text", "")) for p in parts
        if isinstance(p, dict) and not p.get("thought")
    )


def _analytics_manager_called_approval_tool(session_events: list, csv_path: str | None = None) -> bool:
    for i, raw_event in enumerate(session_events):
        event = _extract_event_dict(raw_event)
        if event.get("author") != "analytics_manager":
            continue
        content = event.get("content") or {}
        parts = content.get("parts", [])
        for p in parts:
            if not isinstance(p, dict):
                continue
            fc = p.get("function_call")
            if fc and isinstance(fc, dict) and fc.get("name") == "request_pipeline_approval":
                if csv_path:
                    args = fc.get("args", {})
                    if isinstance(args, dict):
                        approved_path = args.get("file_path", "")
                        _log("[APPROVAL_SCAN] event@%s author=analytics_manager approved_path=%s looking_for=%s",
                             i, approved_path, csv_path)
                        if approved_path and approved_path != csv_path:
                            continue
                _log("[APPROVAL_SCAN] MATCH at event@%s csv_path=%s", i, csv_path)
                return True
    _log("[APPROVAL_SCAN] no match found csv_path=%s", csv_path)
    return False

def universal_deserialize(raw_input: Any) -> dict:
    """
    SOLUTION 5 PATTERN: Recursively unpacks and flattens model string outputs.
    Continues peeling back string layers until a valid dictionary is reached.
    """
    if isinstance(raw_input, dict):
        return raw_input
        
    if isinstance(raw_input, str):
        cleaned = raw_input.strip()
        cleaned = re.sub(r"^```json\s*|\s*```$", "", cleaned, flags=re.MULTILINE).strip()
        
        json_match = re.search(r"\{.*?\}", cleaned, re.DOTALL)
        if json_match:
            try:
                return universal_deserialize(json.loads(json_match.group(0)))
            except json.JSONDecodeError:
                pass
                
        try:
            return universal_deserialize(json.loads(cleaned))
        except json.JSONDecodeError:
            return {"next_step": cleaned.upper()}
            
    return {}

def _parse_analyst_decision(flattened: dict) -> str:
    decision = str(flattened.get("next_step", "SCIENTIST")).strip().upper()
    if "ENGINEER" in decision:
        return "data_engineer"
    return "data_scientist"

def analyst_decision_router(ctx: Any) -> Any:
    session_events = getattr(ctx, 'events', []) or getattr(getattr(ctx, 'session', None), 'events', [])
    if not session_events:
        return Event(route="data_engineer", output={"status": "SUCCESS"})

    for raw_event in reversed(session_events):
        event = _extract_event_dict(raw_event)
        if event.get("author") != "data_analyst":
            continue
        full_raw_text = _get_event_text(event)
        if not full_raw_text.strip():
            continue
        flattened_data = universal_deserialize(full_raw_text)
        if "next_step" in flattened_data:
            route = _parse_analyst_decision(flattened_data)
            return Event(route=route, output=flattened_data)

    return Event(route="data_scientist", output={})

# ==========================================================
# STAR TOPOLOGY: Central Hub Router
# Attached to analytics_manager to decide which spoke to activate next.
# ==========================================================

def _get_session_events(ctx: Any) -> list:
    return (
        getattr(ctx, "events", [])
        or getattr(getattr(ctx, "session", None), "events", [])
    )

def _get_last_spoke_author(session_events: list) -> str:
    SPOKE_AUTHORS = {
        "data_engineer", "data_analyst", "data_scientist", "business_analyst",
        "senior_analytics_manager",
    }
    for raw_event in reversed(session_events):
        event = _extract_event_dict(raw_event)
        if event.get("author", "") in SPOKE_AUTHORS:
            return event["author"]
    return ""

_CSV_PATH_RE = re.compile(
    r'((?:/[a-zA-Z0-9._/-]+|[a-zA-Z0-9._][a-zA-Z0-9._/-]*)\.csv)'
)
_SHELL_META_RE = re.compile(r'[;|`$(){}<>!&\'"]')
_AFFIRMATIVE_RE = re.compile(
    r'^\s*(yes|yeah|yep|sure|ok|okay|go ahead|proceed|do it|start|please do)\b',
    re.IGNORECASE
)


def _has_user_message_after(before_author: str, session_events: list) -> bool:
    last_idx = -1
    for i, raw_event in enumerate(session_events):
        event = _extract_event_dict(raw_event)
        if event.get("author") == before_author:
            last_idx = i
    if last_idx == -1:
        _log("[HAS_USER_AFTER] %s not found in events", before_author)
        return False
    for i in range(last_idx + 1, len(session_events)):
        event = _extract_event_dict(session_events[i])
        if event.get("author") == "user":
            _log("[HAS_USER_AFTER] user message found at event@%s after %s", i, before_author)
            return True
    _log("[HAS_USER_AFTER] no user message after %s (last at event@%s)", before_author, last_idx)
    return False


def _validate_csv_path(path: str) -> str | None:
    if ".." in path or path.startswith("~"):
        return None
    if _SHELL_META_RE.search(path):
        return None
    if not path.lower().endswith(".csv"):
        return None
    return path


def _analytics_manager_approved(session_events: list, csv_path: str | None = None) -> bool:
    return _analytics_manager_called_approval_tool(session_events, csv_path)


def _user_affirmed_after_ask(session_events: list) -> bool:
    last_user_text = ""
    last_manager_asked = False
    for raw_event in reversed(session_events):
        event = _extract_event_dict(raw_event)
        author = event.get("author", "")
        text = _get_event_text(event).strip().lower()
        if author == "user" and not last_user_text:
            last_user_text = text
        elif author == "analytics_manager" and not last_manager_asked:
            if "shall i proceed" in text or "proceed with the pipeline" in text:
                last_manager_asked = True
        if last_user_text and last_manager_asked:
            matched = bool(_AFFIRMATIVE_RE.search(last_user_text))
            _log("[AFFIRM_CHECK] user_text=%s manager_asked=True matched=%s", last_user_text, matched)
            return matched
        if last_user_text and author == "analytics_manager":
            _log("[AFFIRM_CHECK] user_text=%s but no manager ask found before break", last_user_text)
            break
    _log("[AFFIRM_CHECK] no affirmation found (user_text=%s manager_asked=%s)", last_user_text, last_manager_asked)
    return False


def _deduplicate_user_input(text: str) -> str:
    half = len(text) // 2
    if half > 0 and text[:half] == text[half:]:
        return text[:half]
    return text

def _find_csv_path_in_user_messages(session_events: list) -> str | None:
    seen = set()
    for raw_event in reversed(session_events):
        event = _extract_event_dict(raw_event)
        if event.get("author") != "user":
            continue
        text = _deduplicate_user_input(_get_event_text(event))
        for path in _CSV_PATH_RE.findall(text.lower()):
            validated = _validate_csv_path(path)
            if validated is None:
                _log("[CSV_FIND] rejecting path=%s (validation failed)", path)
                continue
            if validated in seen:
                _log("[CSV_FIND] skipping path=%s (already seen)", path)
                continue
            seen.add(validated)
            if os.path.exists(path) or path.count("/") >= 1:
                _log("[CSV_FIND] FOUND path=%s", validated)
                return validated
            _log("[CSV_FIND] path=%s has no '/' and doesn't exist — skipping", path)
    _log("[CSV_FIND] no CSV found in user messages")
    return None

def manager_decision_router(ctx: Any) -> Any:
    from ai_analytics_department.schemas.shared_data import data_container as _dc
    session_events = _get_session_events(ctx)
    last_author = _get_last_spoke_author(session_events)
    event_count = len(session_events)

    _log("[ROUTER_ENTER] events=%s last_spoke=%s pc=%s csv=%s cycle=%s",
         event_count, last_author, _dc.pipeline_complete, _dc.current_csv_path, _dc.pipeline_cycle)

    if last_author == "senior_analytics_manager":
        has_user = _has_user_message_after("senior_analytics_manager", session_events)
        _log("[SENIOR_BRANCH] has_user_after=%s pipeline_complete=%s", has_user, _dc.pipeline_complete)
        if not has_user:
            if _dc.pipeline_complete:
                _log("[ROUTE] → END (qa_standby)")
                return Event(route="END", output={"mode": "qa_standby"})
            _log("[ROUTE] → senior_analytics_manager (qa)")
            return Event(route="senior_analytics_manager", output={"mode": "qa"})

    if last_author == "business_analyst":
        _dc.pipeline_complete = True
        _log("[ROUTE] → senior_analytics_manager (PIPELINE_COMPLETE) pc=True")
        return Event(route="senior_analytics_manager", output={"status": "PIPELINE_COMPLETE"})

    if last_author == "data_scientist":
        _log("[ROUTE] → business_analyst")
        return Event(route="business_analyst", output={"status": "SUCCESS"})

    if last_author == "data_analyst":
        for raw_event in reversed(session_events):
            event = _extract_event_dict(raw_event)
            if event.get("author") != "data_analyst":
                continue
            full_raw_text = _get_event_text(event)
            if not full_raw_text.strip():
                continue
            flattened = universal_deserialize(full_raw_text)
            route = _parse_analyst_decision(flattened)
            _log("[ROUTE] → %s (analyst decision)", route)
            return Event(route=route, output=flattened)
        _log("[ROUTE] → data_scientist (analyst default)")
        return Event(route="data_scientist", output={"status": "SUCCESS"})

    if last_author == "data_engineer":
        analyst_input = _dc.raw_data if _dc.raw_data else {"status": "SUCCESS"}
        if _dc.current_csv_path and not _dc.pipeline_complete and _dc.df.empty:
            _log("[ROUTE] → END (data_load_failed) df empty after engineer")
            error_msg = "Data loading failed."
            if _dc.raw_data and isinstance(_dc.raw_data, dict) and "error" in _dc.raw_data:
                error_msg = _dc.raw_data["error"]
            return Event(route="END", output={"status": "ERROR", "error": error_msg})
        _log("[ROUTE] → data_analyst")
        return Event(route="data_analyst", output=analyst_input)

    csv_path = _find_csv_path_in_user_messages(session_events)

    # Suppress re-processing of an already-completed CSV
    if csv_path and _dc.pipeline_complete and csv_path == _dc.current_csv_path:
        _log("[CSV_SUPPRESS] pc=True csv=%s == current_csv — suppressing", csv_path)
        csv_path = None

    if csv_path:
        approved = _analytics_manager_approved(session_events, csv_path)
        affirmed = _user_affirmed_after_ask(session_events)
        _log("[CSV_CHECK] csv=%s approved=%s affirmed=%s", csv_path, approved, affirmed)
        if approved or affirmed:
            _dc.pipeline_complete = False
            _dc.current_csv_path = csv_path
            _dc.pipeline_cycle += 1
            _log("[ROUTE] → data_engineer (PIPELINE_START cycle=%s path=%s)", _dc.pipeline_cycle, csv_path)
            return Event(route="data_engineer", output={
                "status": "PIPELINE_START", "file_path": csv_path,
                "pipeline_cycle": _dc.pipeline_cycle,
            })

    if csv_path and csv_path != _dc.current_csv_path:
        _log("[CSV_NEW] csv=%s != current=%s — waiting for approval (pc left intact)", csv_path, _dc.current_csv_path)
        return Event(route="END", output={"status": "CONVERSATIONAL_MODE"})

    if _dc.pipeline_complete:
        _log("[ROUTE] → senior_analytics_manager (qa mode)")
        return Event(route="senior_analytics_manager", output={"mode": "qa"})

    _log("[ROUTE] → END (conversational)")
    return Event(route="END", output={"status": "CONVERSATIONAL_MODE"})
