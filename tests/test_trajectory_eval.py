import os
import json
import asyncio
import sys
import pytest
from datetime import datetime
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.apps.llm_event_summarizer import Content, Part
from ai_analytics_department.workflows.graph_workflow import compiled_workflow
from ai_analytics_department.workflows.router import _diag_off

_diag_off()

CSV_REL = "data/raw/house-prices-advanced-regression-techniques/adk_train.csv"


def _find_csv() -> str:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    path = os.path.join(repo_root, CSV_REL)
    if not os.path.exists(path):
        pytest.skip(f"Test CSV not found at {path}")
    return path


EVAL_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs", "eval")


def _save_summary(routes, tool_calls, score=None, reasoning=None):
    os.makedirs(EVAL_OUTPUT_DIR, exist_ok=True)
    summary = {
        "timestamp": datetime.now().isoformat(),
        "routes": routes,
        "score": score,
        "reasoning": reasoning,
    }
    path = os.path.join(EVAL_OUTPUT_DIR, "trajectory_latest.json")
    with open(path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    link = os.path.join(EVAL_OUTPUT_DIR, "trajectory_latest.json")
    print(f"   📁 Summary saved: {link}", file=sys.stderr)


def _extract_routes(events: list) -> list[str]:
    return [
        e.actions.route
        for e in events
        if e.actions and e.actions.route
    ]


def _extract_tool_calls(events: list) -> dict[str, list[str]]:
    calls: dict[str, list[str]] = {}
    for e in events:
        parts = e.content.parts if e.content else []
        for p in parts:
            if p.function_call:
                calls.setdefault(e.author or "unknown", []).append(
                    p.function_call.name or ""
                )
    return calls


def _extract_metric(events: list) -> float | None:
    for e in events:
        parts = e.content.parts if e.content else []
        for p in parts:
            if p.function_response and p.function_response.response:
                resp = p.function_response.response
                if isinstance(resp, dict):
                    for key in ("r_squared", "r2_score", "r2", "score"):
                        val = resp.get(key)
                        if val is not None:
                            try:
                                return float(val)
                            except (ValueError, TypeError):
                                pass
                text = str(resp)
                for token in ("r_squared", "r2_score", "r2", "r²", "R²"):
                    idx = text.lower().find(token)
                    if idx >= 0:
                        chunk = text[idx : idx + 30]
                        for word in chunk.replace(",", " ").split():
                            try:
                                return float(word)
                            except ValueError:
                                continue
    return None


def _build_judge_prompt(
    routes: list[str],
    tool_calls: dict[str, list[str]],
    r2: float | None,
) -> str:
    expected = [
        "data_engineer",
        "data_analyst",
        "data_scientist",
        "business_analyst",
        "senior_analytics_manager",
    ]
    order_ok = all(a == b for a, b in zip(
        [r for r in routes if r in expected],
        expected,
    ))
    all_present = all(e in routes for e in expected)
    tool_summary = "\n".join(
        f"  {author}: {', '.join(calls) if calls else '(none)'}"
        for author, calls in tool_calls.items()
    )
    return f"""You are a judge evaluating an AI agent pipeline.

Expected route sequence: data_engineer → data_analyst → data_scientist → business_analyst → senior_analytics_manager

Observed routes: {routes}
All expected agents present: {all_present}
Correct order: {order_ok}
R² score produced: {r2 if r2 is not None else 'not found'}

Tool calls per agent:
{tool_summary}

Score this session 0-10 based on:
1. All expected agents were activated (0-3 points)
2. Agents activated in the correct order (0-3 points)
3. Each agent called appropriate tools for its role (0-2 points)
4. Pipeline completed with meaningful output such as graphs, PDF, R² (0-2 points)

Respond with ONLY valid JSON: {{"score": <int>, "reasoning": "<brief explanation>"}}"""


@pytest.mark.slow
def test_pipeline_trajectory():
    from litellm import acompletion

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        pytest.skip("GEMINI_API_KEY not set — trajectory eval requires live API")

    csv_path = _find_csv()

    async def _run_pipeline() -> list:
        session_service = InMemorySessionService()
        runner = Runner(
            agent=compiled_workflow,
            session_service=session_service,
            app_name="ai_analytics_department",
            auto_create_session=True,
        )
        all_events: list = []

        content = Content(role="user", parts=[Part(text=csv_path)])
        async for event in runner.run_async(
            user_id="trajectory_eval",
            session_id="eval_session_1",
            new_message=content,
        ):
            all_events.append(event)

        yes_content = Content(role="user", parts=[Part(text="yes")])
        async for event in runner.run_async(
            user_id="trajectory_eval",
            session_id="eval_session_1",
            new_message=yes_content,
        ):
            all_events.append(event)

        return all_events

    events = asyncio.run(_run_pipeline())

    routes = _extract_routes(events)
    tool_calls = _extract_tool_calls(events)
    r2 = _extract_metric(events)

    judge_prompt = _build_judge_prompt(routes, tool_calls, r2)

    async def _judge() -> tuple[int, str]:
        import asyncio as _asyncio
        import random as _random
        delay = 4.0
        for attempt in range(4):
            try:
                resp = await acompletion(
                    model="gemini/gemini-flash-latest",
                    messages=[{"role": "user", "content": judge_prompt}],
                )
                text = resp.choices[0].message.content or ""
                text = text.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[-1]
                    text = text.rsplit("```", 1)[0]
                parsed = json.loads(text)
                return parsed.get("score", 0), parsed.get("reasoning", "")
            except Exception:
                if attempt < 3:
                    wait = delay * _random.uniform(0.75, 1.25)
                    print(f"⏳ Judge LLM call failed, retrying in {wait:.0f}s...")
                    await _asyncio.sleep(wait)
                    delay *= 2
                else:
                    raise
        return 0, "judge LLM failed after retries"

    _save_summary(routes, tool_calls)

    print(f"\n📊 TRAJECTORY EVAL RESULTS", file=sys.stderr)
    print(f"   Routes: {routes}", file=sys.stderr)
    print(f"   R² metric: {r2}", file=sys.stderr)
    print(f"   Tool calls: {json.dumps(tool_calls, indent=2)}", file=sys.stderr)

    try:
        score, reasoning = asyncio.run(_judge())
        _save_summary(routes, tool_calls, score, reasoning)
        print(f"   Judge score: {score}/10", file=sys.stderr)
        print(f"   Reasoning: {reasoning}", file=sys.stderr)
        assert score >= 6, (
            f"Trajectory score {score}/10 below threshold 6.\n"
            f"Reasoning: {reasoning}\n"
            f"Routes: {routes}\n"
            f"Tool calls: {json.dumps(tool_calls, indent=2)}\n"
            f"R²: {r2}"
        )
    except Exception as judge_err:
        print(f"   ⚠️ Judge LLM unavailable: {judge_err}", file=sys.stderr)
        print(f"   📁 Summary saved to outputs/eval/trajectory_latest.json", file=sys.stderr)
        expected = {"data_engineer", "data_analyst", "data_scientist",
                     "business_analyst", "senior_analytics_manager"}
        route_set = set(routes)
        missing = expected - route_set
        assert not missing, (
            f"Pipeline did not activate all expected agents. "
            f"Missing: {missing}. Routes: {routes}"
        )
        assert r2 is not None, "Pipeline completed but no R² metric found in events"
