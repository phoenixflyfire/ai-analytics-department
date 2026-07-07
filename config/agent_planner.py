"""Central toggle for agent reasoning/thought output.

Set SUPPRESS_THOUGHTS = False to restore model thinking display in the UI.
"""
from google.adk.planners import BuiltInPlanner
from google.genai import types

SUPPRESS_THOUGHTS = True

_planner = None


def get_planner():
    global _planner
    if SUPPRESS_THOUGHTS and _planner is None:
        _planner = BuiltInPlanner(
            thinking_config=types.ThinkingConfig(include_thoughts=False)
        )
    return _planner if SUPPRESS_THOUGHTS else None
