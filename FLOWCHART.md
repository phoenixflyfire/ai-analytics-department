# AI Analytics Department — Program Flow

```
┌────────────────────────────────────────────────────────┐
│  ENTRY: agent.py                                       │
│  exports root_agent = compiled_workflow                │
│  ADK engine starts here (adk web / adk run)            │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│  entry_gate (function node)                            │
│  ┌──────────────┐      ┌──────────────────────────┐    │
│  │ pipeline     │      │ pipeline_complete = true │    │
│  │ not complete │      │ + user message has CSV   │    │
│  └──────┬───────┘      │ → reset, route to hub    │    │
│         │              └──────────┬───────────────┘    │
│         ▼                         ▼                    │
│  analytics_manager      ┌────────────────────────┐     │
│  (hub agent)            │pipeline_complete = true│     │
│                         │ + no CSV → direct to   │     │
│                         │ senior_analytics_mgr   │     │
│                         └────────────────────────┘     │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│  analytics_manager (HUB AGENT - single_turn)           │
│                                                        │
│  Role: Gatekeeper                                      │
│  - Greets user                                         │
│  - Detects CSV path in user message                    │
│  - Calls request_pipeline_approval (HITL tool)         │
│  - "Shall I proceed with the pipeline?" → user affirms │
│                                                        │
│  Tools: [approve_pipeline_tool]                        │
└────────────────────┬───────────────────────────────────┘
                     │  output
                     ▼
┌──────────────────────────────────────────────────────────────────┐
│  manager_decision_router (CENTRAL DISPATCH)                      │
│                                                                  │
│  Reads: session events, data_container state                     │
│  Decides: which spoke to activate next based on:                 │
│   - last spoke author (data_engineer? data_analyst? etc.)        │
│   - pipeline_complete flag                                       │
│   - CSV path found in user messages                              │
│   - HITL approval status                                         │
│                                                                  │
│  ┌─────────────┐  ┌──────────┐  ┌────────────┐  ┌──────────┐     │       
│  │ last:       │  │ last:    │  │ last:      │  │ last:    │     │    
│  │ engineer    │  │ analyst  │  │ scientist  │  │ business │     │    
│  │ → analyst   │  │→scientist│  │ → business │  │ → senior │     │    
│  │             │  │or engr*  │  │   analyst  │  │   (DONE) │     │    
│  └─────────────┘  └──────────┘  └────────────┘  └──────────┘     │    
│  *analyst returns next_step in JSON                              │
│                                                                  │
│  CSV discovered + approved → reset pipeline → engineer           │
│  Pipeline complete → senior_analytics_manager (QA mode)          │
│  No CSV, no pipeline → END (conversational mode)                 │
└───────┬──────────────┬──────────────┬──────────────┬────────────┘
        │              │              │              │
        ▼              ▼              ▼              ▼
   ┌─────────┐   ┌──────────┐  ┌────────────┐  ┌──────────────────┐
   │ data_   │   │ data_    │  │ data_      │  │ senior_analytics │
   │ engineer │   │ analyst  │  │ scientist  │  │ _manager         
   └────┬────┘   └────┬─────┘  └─────┬──────┘  └────────┬─────────┘
        │             │              │                   │
        ▼             ▼              ▼                   ▼
┌──────────────┐ ┌────────────--┐ ┌──────────────┐ ┌──────────────────┐
│ DATA ENGINEER│ │DATA ANALYST  │ │DATA SCIENTIST│ │SENIOR ANALYTICS  │
│ (single_turn)│ │(single_turn) │ │(single_turn) │ │MANAGER (post-    │
│              │ │              │ │              │ │pipeline Q&A)     │
│ Skill: data- │ │ Skill:       │ │ Skill:       │ │                  │
│ engineering  │ │ data-        │ │ modeling     │ │Tools: get_schema,│
│              │ │ analysis     │ │              │ │query_df          │
│ Tool:        │ │              │ │ Tool:        │ │+ MCP Toolset:    │
│ load_dataset │ │ Tool:        │ │train_house_  │ │ mcp_load_csv     │
│              │ │ run_eda      │ │price_model   │ │ mcp_get_schema   │
│ Writes to    │ │              │ │              │ │ mcp_query_csv    │
│ data_cont-   │ │ Reads df     │ │ Reads df     │ │ mcp_compare_     │
│ ainer.df     │ │ Returns      │ │ Returns R²   │ │   datasets       │
│              │ │ next_step    │ │              │ │ mcp_deploy_to_   │
│              │ │ SCIENTIST    │ │              │ │   cloud_run      │
│              │ │ or ENGR      │ │              │ │                  │
└──────┬───────┘ └────┬─────----┘ └──────┬───────┘ └──────┬───────────┘
       │              │              │                    │
       ▼              │              │                    │
┌──────────────┐      │              ▼                    │
│engineer_     │      │       ┌──────────────┐            │
│output_       │      │       │business_     │            │
│adapter       │      │       │input_adapter │            │
│(transforms   │      │       │(transforms   │            │
│tool output)  │      │       │sci output)   │            │
└──────┬───────┘      │       └──────┬───────┘            │  
       │              │              │                    │
       └──────────────┴──────────────┘                    │
                      │                                   │
                      ▼                                   │
          ┌──────────────────────┐                        │
          │  BUSINESS ANALYST    │◄──────────────────-----┘
          │  (single_turn)       │   (after pipeline complete)
          │                      │
          │  Skill: business-    │
          │  reporting           │
          │                      │
          │  Tools:              │
          │  create_saleprice_   │
          │    distribution      │
          │  create_correlation_ │
          │    chart             │
          │  save_report_as_pdf  │
          │                      │
          │  Output: PDF report  │
          └──────────┬───────────┘
                     │  routes back to hub
                     │  router sets pipeline_complete=True
                     ▼
          ┌──────────────────────┐
          │  senior_analytics_   │
          │  manager (QA mode)   │
          │                      │
          │  "Pipeline complete!"│
          │  Proactively offers: │
          │  - Test CSV compare  │
          │  - Cloud Run deploy  │
          │  - Q&A on data       │
          │  - New CSV analysis  │
          └──────────┬───────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │  ROUTER (again)      │
          │                      │
          │  User replied?       │
          │  ├─ No → END         │
          │  ├─ New CSV →        │
          │  │  approval → reset │
          │  │  → engineer       │
          │  └─ Question →       │
          │     senior_analytics │
          │     _manager again   │
          └──────────────────────┘
```

## Data Flow (side channel, not through LLM context)

```
DataContainer (singleton in schemas/shared_data.py)
┌──────────────────────────────────────────────────┐
│  df: pd.DataFrame           ← engineer writes    │
│  raw_data: dict             ← adapter writes     │
│  pipeline_complete: bool    ← router sets        │
│  current_csv_path: str      ← router tracks      │
│  pipeline_cycle: int        ← increments per run │
└──────────────────────────────────────────────────┘
            ▲                           │
            │  reads by analyst,        │  written by
            │  scientist, senior        │  engineer, adapters
            └───────────────────────────┘
```

## MCP Server (subprocess, isolated from pipeline)

```
mcp_server/server.py ── FastMCP, connected via McpToolset
┌─────────────────────────────────────────────────-┐
│  mcp_load_csv(file_path) → loads into _loaded_dfs│
│  mcp_get_schema(file_path) → schema analysis     │
│  mcp_query_csv(file_path, ...) → stats/describe  │
│  mcp_compare_datasets(a, b) → cross-file diff    │
│  mcp_deploy_to_cloud_run(...) → Cloud Run deploy │
└─────────────────────────────────────────────────-┘
  Only accessible to senior_analytics_manager agent
  Does NOT use data_container.df — fully isolated
```

## Agent Directory

| Agent                           | Mode         | Role                   | Tools / Skills                                                                             |
|--------------------------        |-------------|------------------------          |--------------------------------------------------------------                 |
| `analytics_manager`              | single_turn  | Hub — gatekeeper, HITL | `request_pipeline_approval`                                  |
| `data_engineer`                  | single_turn  | Loads CSV into shared DF | Skill: data-engineering + `load_dataset`                     |
| `data_analyst`                   | single_turn  | Exploratory data analysis | Skill: data-analysis + `run_eda`                             |
| `data_scientist`                 | single_turn  | ML model training      | Skill: modeling + `train_house_price_model`                  |
| `business_analyst`               | single_turn  | Charts + PDF report    | Skill: business-reporting + visualization tools + `save_report_as_pdf` |
| `senior_analytics_manager`       | single_turn  | Post-pipeline Q&A + MCP | `get_schema`, `query_df` + 5 MCP tools                       |

## Key Routing Decisions

| Condition | Route | Reasoning |
|---|---|---|
| No pipeline, no CSV | `END` | Conversational mode — user is chatting |
| CSV found + approved | `data_engineer` | Start new pipeline cycle |
| After engineer | `data_analyst` | Move to EDA stage |
| After analyst | `data_scientist` or `data_engineer` | Analyst's `next_step` JSON decides |
| After scientist | `business_analyst` | Generate charts + PDF |
| After business analyst | `senior_analytics_manager` | Mark pipeline_complete=True, enter Q&A |
| Senior + user question | `senior_analytics_manager` | Stay in Q&A loop |
| Senior + new CSV path | Approval check → reset | New pipeline cycle |
| Senior + no user reply | `END` | Standby mode |

## File → Role Map

| File | Responsibility |
|---|---|
| `agent.py` | Entry point — exports `root_agent` |
| `workflows/graph_workflow.py` | Graph edges, entry_gate, routing maps |
| `workflows/router.py` | Central dispatch logic, CSV validation, HITL checks |
| `schemas/shared_data.py` | `DataContainer` singleton (df, raw_data, state) |
| `schemas/schemas.py` | Pydantic models (RawData, AdapterInput, etc.) |
| `config/model_config.py` | Model selection per agent |
| `config/agent_planner.py` | Thought suppression toggle |
| `utils/model_client.py` | `_RetryLiteLlm` — retry wrapper + thought filter |
| `tools/` | Function tools (data_loader, eda, modeling, visualization, reporting, hitl, data_query) |
| `skills/__init__.py` | 4 inline Skills + SkillToolset factories |
| `mcp_server/server.py` | FastMCP server — 5 MCP tools |
| `tests/test_star_topology.py` | 29 integration tests |
