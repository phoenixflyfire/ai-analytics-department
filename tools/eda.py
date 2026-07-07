# ==========================================================
# ai_analytics_department/tools/eda.py
# ==========================================================
# ==========================================================
# This file is merged with function engineer_output_adapter
# ==========================================================

import pandas as pd
from typing import Any
import json
from ai_analytics_department.schemas.schemas import RawData
from ai_analytics_department.workflows.router import _extract_event_dict

def engineer_output_adapter(ctx: Any) -> RawData:
    session_events = getattr(ctx, 'events', []) or getattr(getattr(ctx, 'session', None), 'events', [])
    for raw_event in reversed(session_events):
        event = _extract_event_dict(raw_event)
        content = event.get("content")
        if not content or not isinstance(content, dict):
            continue
        for part in content.get("parts", []):
            if isinstance(part, dict) and "functionResponse" in part:
                resp = part["functionResponse"].get("response", {})
                if isinstance(resp, dict) and resp.get("data_content"):
                    result = RawData(**resp)
                else:
                    result = RawData(data_content=json.dumps(resp), source="loaded_from_csv")
                data_container.raw_data = result.model_dump()
                return result
    for raw_event in reversed(session_events):
        event = _extract_event_dict(raw_event)
        if event.get("author") == "data_engineer" and data_container.df.empty:
            result = RawData(
                data_content=json.dumps({"status": "ERROR", "error": "Data loading failed - no data loaded"}),
                source="loaded_from_csv"
            )
            data_container.raw_data = result.model_dump()
            return result
    result = RawData(data_content=json.dumps({"status": "SUCCESS"}), source="pipeline_init")
    data_container.raw_data = result.model_dump()
    return result

from ai_analytics_department.schemas.shared_data import data_container

def run_eda() -> dict:
    if data_container.df.empty:
        return {
            "status": "NO_DATA",
            "rows": 0,
            "columns": 0,
            "missing_values": 0,
            "source": "exploratory_data_analysis"
        }

    df = data_container.df
    rows = len(df)
    columns = len(df.columns)
    missing_values = int(df.isnull().sum().sum())

    return {
        "status": "SUCCESS",
        "rows": rows,
        "columns": columns,
        "missing_values": missing_values,
        "source": "exploratory_data_analysis"
    }
