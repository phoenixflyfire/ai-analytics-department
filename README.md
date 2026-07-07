# ai-analytics-department
A Google ADK 2.3.0 multi-agent AI analytics system powered by Gemini AI Models, that delivers end‑to‑end data analysis and machine‑learning via a star‑topology workflow. Ingest any CSV and text files of datasets, watch agents execute the pipeline step‑by‑step, and then interact with the results with a Senior Analyst powered by MCP tools.

📖 Project Overview → [Watch the 2‑minute demo on YouTube](https://www.youtube.com/)

## TL;DR
- **Main intro / front‑facing story:** `KAGGLE_WRITEUP.md` (For the project narrative, motivation, and Kaggle‑submission details)
- **Technical how‑to / reference:** `README.md` (with a brief link back to the write‑up)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-311/)
[![ADK 2.3.0](https://img.shields.io/badge/ADK-2.3.0-brightgreen.svg)](https://google.github.io/adk-docs/)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](https://github.com/your-username/ai-analytics-department/actions)



## What it does
- **Data Engineer** – loads the CSV into a shared in‑memory `DataFrame`.
- **Data Analyst** – runs exploratory data analysis (row/column counts, missing values).
- **Data Scientist** – trains a `RandomForestRegressor` and reports the R² score.
- **Business Analyst** – builds distribution & correlation charts and saves a PDF report.
- **Analytics Manager (Hub)** – handles the Human‑in‑the‑Loop (HITL) approval gate and routes requests.
- **Senior Analytics Manager** – post‑pipeline Q&A powered by MCP tools (schema, query, cross‑file compare).

## Architecture
The system follows a **star‑topology directed graph**: the `analytics_manager` hub owns the conversation; all specialist agents are spokes that return control to the hub after each turn. A `manager_decision_router` inspects session history to decide the next spoke.

```
User ──→ START ──→ entry_gate (function)
                   │
              ┌────┴────┐
              │  quick  │  (has CSV/TXT path?)
              │  Q&A?   │
              └────┬────┘
         ┌─────────┼─────────┐
         ▼                   ▼
senior_analytics      analytics_manager (HUB)
_manager (Q&A)              │
                             ▼ (manager_decision_router)
                        ┌────┴────┐
                        │ spoke?  │
                        └────┬────┘
                   ┌─────────┼─────────┐
                   ▼         ▼         ▼
              engineer  analyst  scientist  business_analyst
                   │         │         │         │
                   └─────────┴─────────┴─────────┘
                             │ (all route back)
                             ▼
                       analytics_manager → router → NEXT or END
                                              └→ senior_analytics_manager (Q&A)
```

![pipeline_workflow](data/processed/pipeline_workflow.png)


## Key Design Decisions

- **Star topology** – central hub owns conversation; spokes are stateless workers that return control, preventing agents from talking past each other.
- **Router‑driven dispatch** – `manager_decision_router` decides the next spoke based on session history; no hard‑coded linear chain.
- **Shared DataFrame** – tools read/write `schemas/shared_data.data_container.df` instead of moving large data through LLM context windows.
- **Adapter functions** – convert raw tool output into structured input for the next node.
- **Single‑turn agents** – all agents run in `single_turn` mode to avoid infinite loops.
- **Event‑based routing** – routers return `Event(route="spoke_name", output={…})`; ADK matches the route to `SPOKE_ROUTING_MAP`.

## Project structure
```
ai_analytics_department/
├─ agent.py               # Entry point – exposes root_agent
├─ workflows/
│  ├─ graph_workflow.py   # Star‑topology edge definitions
│  └─ router.py           # Hub decision logic + serialization
├─ agents/                # 6 specialized agents
├─ tools/                 # Action tools + adapters
├─ schemas/               # Pydantic models & shared DataContainer
├─ mcp_server/            # FastMCP server (4 MCP tools)
├─ skills/                # SkillToolset definitions
├─ utils/                 # Retry wrapper, model client
└─ config/                # Model selection (Gemini/model_config.py)
```

## Shared data
Tools share a `DataFrame` via `schemas/shared_data.DataContainer`. The `data_engineer` loads the CSV/TXT into `data_container.df`; subsequent agents read from it.

## Quick start
```bash
# 1️⃣ Clone & enter
git clone https://github.com/your-username/ai-analytics-department.git
cd ai-analytics-department

# 2️⃣ Create virtualenv & install deps
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install google-adk   # pulls ADK 2.3.0

# 3️⃣ Configure model (edit config/model_config.py or export vars)
# Example for Gemini via LiteLLM
export GEMINI_API_KEY="your-key"
# Optionally edit config/model_config.py to set MODEL, PROVIDER, etc.

# 4️⃣ Run the ADK web UI
adk web   # opens http://127.0.0.1:8000
# or use the helper scripts:
# ./start_adk.sh
# ./stop_adk.sh
# ./run_adk.sh
```

## Deployment (Cloud Run)
You can deploy to Google Cloud Run with the ADK CLI or a manual Docker build.

### Agent-assisted Deployment
Enter Prompt: `Deploy this project to Google Cloud Run using ADK's cloud_run deploy command.`
Requires: Google Cloud project + billing, `gcloud` SDK, enabled Cloud Run / Artifact Registry / Cloud Build APIs.

### Using ADK CLI
```bash
adk deploy cloud_run \
  --project=YOUR_GCP_PROJECT \
  --region=us-central1 \
  --service_name=ai-analytics-dept \
  .
```
### Manual Docker build
```bash
docker build -t ai-analytics-dept .
docker run -p 8080:8080 -e GEMINI_API_KEY="your-key" ai-analytics-dept
```
*Requires:* a Google Cloud project with billing enabled, the `gcloud` SDK, and the Cloud Run / Artifact Registry / Cloud Build APIs enabled.

## Troubleshooting
- **“cancelling 1 leftover tasks”** in ADK logs → check `local_logs/adk_debug.log` (DEBUG) and `local_logs/ui_console_output.log` (INFO).
- **False‑positive pipeline trigger** → ensure the user message contains an actual path ending in `.csv`; the router logs `Verified CSV path found` when a valid path is detected.
- Verify file paths are correct and accessible from the container/runtime.

## Test suite
```bash
./run_tests.sh   # or
pytest tests/test_star_topology.py -v   # 29 tests covering routing, security, HITL, MCP, etc.
pytest tests/test_trajectory_eval.py -v --slow  # full pipeline + judge LLM scoring (requires GEMINI_API_KEY)
```

## Demo data
A small sample from the House Prices Advanced Regression Techniques dataset is provided under `data/raw/house-prices-advanced-regression-techniques/`.  
- `train.csv` – full training set  
- `test.csv` – test set  
- `train_adk.csv` – a ~1 500‑row subset suitable for quick demos  
- `data_description.txt` - description of features fields

You may substitute any CSV (≈1 000–2 000 rows works well) placed in `data/raw/`.

## How to run a demo
1. Start the ADK UI (`adk web`).
2. In the chat, paste a path to a CSV, e.g.  
   `./data/raw/house-prices-advanced-regression-techniques/adk_train.csv`
3. Answer the HITL prompt with `y`.
4. Watch the agentic flow: Engineer → Analyst → Scientist → Business Analyst.
5. After the PDF report is generated, switch to the Senior Analyst and ask questions, e.g.  
   “Which feature correlates most with SalePrice?”  
   The agent will reply using MCP tools (e.g., `OverallQual 0.79, GrLivArea 0.71`).
6. The generated PDF appears in the `outputs/reports/` folder.

## Converse with this agent at any time:
- You can also converse with this agent at any time
- General questions: ask anything like “How can you help me?” or “What does the model think about feature X?” and the agent will answer using the MCP tools it has access to.
- Load and explore any additional CSV file you provide.
- Conversational capabilities (Senior Analytics Manager):
    Beyond the automated pipeline, the Senior Analyst agent acts as a helpful chatbot you can talk to at any point:
    - Data exploration: view column names, data types, run descriptive stats, spot missing values.
    - Compare the training data with a new test CSV to spot distribution shifts or missing values. 
    - Compare correlation of OverallQual and GrLivArea with SalePrice
    - Which feature correlates most with SalePrice?
    - Do you see any outliers in the data?
    - Ask analytical questions such as “Which feature correlates most with SalePrice?” or “Show me rows with > 5 % missing values.”  
    - Model‑readiness check: upload a test CSV and get a side‑by‑side comparison with the training data (schema diffs, value‑distribution shifts, etc.).  
    - Ad‑hoc file analysis: point it at any other CSV and receive a full profile instantly.  
    - Deployment guidance: receive step‑by‑step instructions (or trigger an automated deploy) for pushing the app to Google Cloud Run when your GCP project is ready.  



## License
MIT – see the `LICENSE` file for details.