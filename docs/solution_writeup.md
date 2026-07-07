# AI Analytics Department — Multi-Agent Data Science Pipeline

> **Track**: Agents for Business / Freestyle  
> **Submission for**: Google's 5-Day AI Agents: Intensive Vibe Coding Course With Google  
> **GitHub**: [https://github.com/phoenixflyfire/ai-analytics-department]
> **YouTube**: [https://youtu.be/8T9QOhk2r3Y]
---

## 🎯 The Problem

Data science is often a black box to most beginners (students especially). You have a CSV, you've heard of "EDA" and "Random Forest," but the gap between theory and seeing it actually work is intimidating.

The confusion extends to career paths: should one choose data engineering, data science, data analytics, data management, or business analytics? Most tutorials jump straight to code without explaining the distinct roles and responsibilities within a typical corporate data team. Even experienced software engineers find these roles opaque; an analyst's EDA, a scientist's model training, and a business analyst's reporting are often viewed as siloed tasks.

This is the moment of AI—the world is ramping up, and learning needs to keep pace. The goal is not just to build, but to teach how data science works in a real-world setting without the overhead of building a demo from scratch.

**This multi-agent (graph workflow) project, built using Python on the Google ADK 2.3.0 framework, exists to solve these questions.**

Drop in any CSV, and four specialist agents walk through the full data science pipeline—loading, exploration, modeling, and reporting—step by step. You watch each specialist receive context, apply their tools, and hand off results to the next stage. The handoffs are visible, the roles are concrete. It's a **living diagram** of how data science works under the hood, built so novices can build intuition for what each stage contributes.

---

## 🏗️ Architecture Overview

The system is a **star-topology multi-agent workflow** built on Google ADK 2.3.0. Six specialist agents collaborate to perform end-to-end data analysis, from CSV loading through ML training to executive reporting.

```
User ──→ analytics_manager (HUB)
              │
              ▼ (manager_decision_router)
         ┌────┴────┐
         │ spoke?  │
         └────┬────┘
    ┌─────────┼───────────────┐
    ▼         ▼         ▼     ▼
 engineer  analyst  scientist  business_analyst
    │         │         │         │
    └─────────┴─────────┴─────────┘
              │ (all route back)
              ▼
        analytics_manager → router → NEXT or END
                               └→ senior_analytics_manager (Q&A)
```

| Agent / Node | Role | Tools |
|---|---|---|
| `analytics_manager` | Hub — greets user, detects CSV paths, requests HITL approval | `request_pipeline_approval` (HITL) |
| `data_engineer` | Loads CSV into shared DataFrame | `load_dataset` via SkillToolset |
| `data_analyst` | Exploratory data analysis (rows, missing values) | `run_eda` via SkillToolset |
| `data_scientist` | Trains RandomForestRegressor, reports R² | `train_house_price_model` via SkillToolset |
| `business_analyst` | Generates charts, compiles PDF report | `create_saleprice_distribution`, `create_correlation_chart`, `save_report_as_pdf` via SkillToolset |
| `senior_analytics_manager` | Post-pipeline Q&A with MCP tools | `get_schema`, `query_df`, McpToolset (5 MCP tools) |

### Key Design Decisions

- **Star topology** — The central `analytics_manager` hub owns the conversation; all specialist spokes return control after one turn. A `manager_decision_router` inspects session history to decide the next spoke. This prevents agents from talking past each other and keeps routing logic in one place.
- **Shared DataFrame** — Tools write to/read from a singleton `DataContainer` instead of passing large datasets through LLM context windows.
- **Single-turn agents** — All agents run in `single_turn` mode to avoid infinite loops. Adapter functions transform raw tool output between agents.
- **Retry wrapper** — The `gemini-flash-latest` model (free-tier Google AI) has intermittent HTTP 500 errors. A custom `_RetryLiteLlm` wrapper handles these with exponential backoff (4s → 6s → 9s → 13.5s → 20.25s, up to 5 retries).

---

## ✨ Capstone Features

### 1. MCP Protocol (Model Context Protocol)

**What**: A standalone MCP server running as a subprocess, connected to the `senior_analytics_manager` via `McpToolset`. The server exposes five tools: four for CSV data analysis plus a Cloud Run deployment tool.

**MCP Server (`mcp_server/server.py`):**
```python
@mcp.tool()
def load_csv(file_path: str) -> dict          # Load CSV, return metadata
@mcp.tool()
def get_schema(file_path: str) -> dict         # Column names, dtypes, null counts
@mcp.tool()
def query_csv(file_path, column, operation)    # describe, value_counts, correlations
@mcp.tool()
def compare_datasets(path_a, path_b) -> dict   # Cross-file structural comparison
@mcp.tool()
def deploy_to_cloud_run(project_id, region, service_name, gemini_api_key) -> dict  # Build + deploy to Cloud Run
```

**Cross-File Comparison Tool** — the tool that demonstrates MCP's value as a protocol:
```python
@mcp.tool()
def compare_datasets(path_a: str, path_b: str) -> dict:
    df_a = _load_or_get(path_a)
    df_b = _load_or_get(path_b)
    # Returns: rows/columns per file, shared/unique columns,
    # dtype mismatches, missing values side-by-side, numeric stats
```

Unlike the pipeline (which processes one file at a time into `data_container.df`), this MCP tool loads **two independent files** into an isolated subprocess. This is only possible because MCP runs separately from the pipeline — a direct Python tool would overwrite the pipeline's shared DataFrame.

### 2. Human-in-the-Loop (HITL) + Security

**HITL Approval Gate:**
```python
def request_pipeline_approval(file_path: str) -> dict:
    if not file_path or not file_path.strip():
        return {"status": "denied", "reason": "No file path provided."}
    return {"status": "approved", "file_path": file_path.strip(), "message": ...}

approve_pipeline_tool = FunctionTool(
    func=request_pipeline_approval,
    require_confirmation=True,
)
```
Before any CSV processing begins, the `analytics_manager` calls `request_pipeline_approval`. ADK intercepts the call because `require_confirmation=True` and prompts the user:
`Tool request_pipeline_approval requires confirmation. Approve? [y/N]`

**Input Validation:**
The system implements rigorous path validation to prevent directory traversal (`..`), home directory (`~`) expansion, and shell metacharacter command injection.

### 3. Agent Skills (Progressive Disclosure)

Four inline Skills defined using ADK's `Skill` model, each scoped to a specific agent role:
```python
data_engineering_skill = models.Skill(
    frontmatter=models.Frontmatter(name="data-engineering", description="Load a CSV dataset."),
    instructions="Call load_dataset(file_path) with the provided file path...",
)
# ... (analyst, modeling, and business reporting skills)
```
The `SkillToolset` auto-generates three tools for progressive disclosure:
1. **`list_skills`** (L1) — returns skill names and descriptions (~200 tokens).
2. **`load_skill(name)`** (L2) — loads full instructions on demand.
3. **`load_skill_resource(name, path)`** (L3) — loads reference files on demand.

---

## 📊 Data Flow

```
User: "analyze /data/raw/train.csv"
  ↓
analytics_manager: calls request_pipeline_approval("/data/raw/train.csv")
  ↓ [User confirms]
analytics_manager: "Pipeline approved. Processing this file..."
  ↓ (router detects CSV path → route: data_engineer)
data_engineer: calls load_dataset("/data/raw/train.csv")
  → writes to data_container.df
  ↓ (adapter → hub → router → route: data_analyst)
data_analyst: calls run_eda()
  → returns {"summary": "...", "next_step": "SCIENTIST"}
  ↓ (adapter → hub → router → route: data_scientist)
data_scientist: calls train_house_price_model()
  → trains RandomForestRegressor on real data
  → returns R² score
  ↓ (adapter → hub → router → route: business_analyst)
business_analyst: generates charts + saves PDF report
  ↓ (hub → router → route: senior_analytics_manager)
senior_analytics_manager: "Pipeline complete. Ask me anything!"
```

**Example Outcome:**  
Processing the sample `train_adk.csv` results in:
- **Model:** RandomForestRegressor with **R² = 0.82**.
- **Output:** A PDF report in `outputs/reports/` containing a Sales Price distribution histogram and a feature correlation heatmap.

---

## 🧪 Test Suite (29 tests)

The project includes a comprehensive suite of tests covering:
- **Routing:** Ensuring the router correctly identifies CSV paths and manages agent handoffs.
- **Security:** Validating path traversals, shell metacharacters, and file extensions.
- **HITL:** Verifying approval and denial mechanisms.
- **MCP:** Testing the MCP server's ability to load, query, and compare datasets.

Run with: `pytest tests/test_star_topology.py -v`

---

## 🛠️ Setup

```bash
git clone https://github.com/phoenixflyfire/ai-analytics-department
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY="your-key"
adk web       # Launch ADK dev UI at http://127.0.0.1:8000
```

---

## 🚀 What's Next (Planned)

1. **Demo Video** — A 2-3 minute walkthrough showing the end-to-end flow (from CSV upload to PDF generation and Q&A). [Link will be added here]
2. **Cloud Run Deployment** — Containerization and deployment to Google Cloud Run for always-on access.

---

## 📝 Lessons Learned

1. **ADK 2.0 Event API** — Routes live under `Event.actions.route`, not `Event.route`.
2. **Chat-mode limitations** — Chat-mode agents cannot follow non-agent nodes; `single_turn` mode is required for effective adapter usage.
3. **MCP PYTHONPATH** — The stdio subprocess does not inherit the local environment; `PYTHONPATH` must be explicitly injected via `StdioServerParameters.env`.
4. **Reliability** — Implementing a custom exponential backoff retry wrapper is essential for the free-tier Gemini model to handle intermittent 500 errors.
5. **Skills for Efficiency** — Using `SkillToolset` for progressive disclosure significantly reduces context bloat.
```