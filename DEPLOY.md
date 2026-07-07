# Cloud Run Deployment Guide

Two options to deploy the AI Analytics Department to Cloud Run.

---

## Option 1: ADK Deploy (Recommended)

The `adk deploy cloud_run` command handles everything — Dockerfile generation, image build, push, and Cloud Run deployment.

### Prerequisites

```bash
# 1. Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init                           # Log in and set project

# 2. Enable required APIs
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com

# 3. Authenticate
gcloud auth login
gcloud auth configure-docker
```

### Deploy

```bash
# From project root
adk deploy cloud_run \
  --project=YOUR_GCP_PROJECT_ID \
  --region=us-central1 \
  --service_name=ai-analytics-dept \
  .
```

**Flags explained**:

| Flag | Value | Why |
|---|---|---|
| `--project` | `your-gcp-project` | GCP project ID (or omit to use `gcloud config get project`) |
| `--region` | `us-central1` | Cloud Run region (us-central1, europe-west1, etc.) |
| `--service_name` | `ai-analytics-dept` | Your Cloud Run service name |
| `.` | (agent path) | Project root — contains `agent.py` with `root_agent` export |

### After Deploy

```bash
# Get the service URL
gcloud run services describe ai-analytics-dept \
  --region=us-central1 \
  --format='value(status.url)'
# → https://ai-analytics-dept-xxxxx-uc.a.run.app
```

You'll also see the URL printed at the end of the deploy output.

---

## Option 2: Manual Docker Build

Use this if you need full control over the Dockerfile.

### Build

```bash
docker build -t ai-analytics-dept .
```

### Test Locally

```bash
docker run -p 8080:8080 \
  -e GEMINI_API_KEY="your-key" \
  ai-analytics-dept
# → Open http://localhost:8080
```

### Push to Artifact Registry

```bash
# Tag for Artifact Registry
docker tag ai-analytics-dept \
  us-central1-docker.pkg.dev/YOUR_PROJECT/cloud-run-source-deploy/ai-analytics-dept

# Push
docker push us-central1-docker.pkg.dev/YOUR_PROJECT/cloud-run-source-deploy/ai-analytics-dept
```

### Deploy to Cloud Run

```bash
gcloud run deploy ai-analytics-dept \
  --image=us-central1-docker.pkg.dev/YOUR_PROJECT/cloud-run-source-deploy/ai-analytics-dept \
  --region=us-central1 \
  --set-env-vars="GEMINI_API_KEY=your-key" \
  --memory=2Gi \
  --cpu=2
```

---

## Verify Deployment

```bash
# Health check
curl -X POST https://your-service-url/ \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","session_id":"test","text":"hello"}'

# Expected: {"response": "Hello! I'm the Analytics Manager..."}
```

Open the URL in a browser for the ADK API server.  
If you want the ADK web UI instead, add `--with_ui` to the deploy command.

---

## Environment Variables

Set these in Cloud Run for proper operation:

| Variable | Required | Notes |
|---|---|---|
| `GEMINI_API_KEY` | Yes | Google AI API key (free tier) |
| `GOOGLE_CLOUD_PROJECT` | Yes | Set automatically by Cloud Run |
| `PYTHONUNBUFFERED` | No | Recommended: `1` for log streaming |

Set via console or CLI:
```bash
gcloud run deploy ai-analytics-dept \
  --update-env-vars=GEMINI_API_KEY=your-key,PYTHONUNBUFFERED=1 \
  --region=us-central1
```

---

## Troubleshooting

### "Cannot import root_agent"
Make sure `agent.py` at the project root exports `root_agent`:
```python
from ai_analytics_department.workflows.graph_workflow import compiled_workflow
root_agent = compiled_workflow
```

### MCP Server Fails in Cloud Run
The MCP subprocess needs `PYTHONPATH` set. The Dockerfile sets it via the parent process. If MCP tools fail, verify:
```
PYTHONPATH=/app:/app:$PYTHONPATH
```
is present in the environment.

### Memory Limits
The scikit-learn model training can use ~500MB RAM. Set Cloud Run memory to at least `1Gi`, recommended `2Gi`.

### Cold Start
First request may take 30-60s (model loading + dependency init). Set `--min-instances=1` if you need zero cold start (costs more).

### Logs
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=ai-analytics-dept" --limit=50
```
