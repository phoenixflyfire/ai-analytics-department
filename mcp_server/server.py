import pandas as pd
from pathlib import Path
from fastmcp import FastMCP

mcp = FastMCP("Data Analysis MCP Server", instructions="CSV data analysis tools. Load a CSV file first, then query it.")

_loaded_dfs: dict[str, pd.DataFrame] = {}


@mcp.tool()
def load_csv(file_path: str) -> dict:
    file_path = file_path.strip()
    resolved = str(Path(file_path).resolve())
    try:
        df = pd.read_csv(resolved)
        _loaded_dfs[resolved] = df
        return {
            "status": "success",
            "path": resolved,
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
def get_schema(file_path: str) -> dict:
    resolved = str(Path(file_path.strip()).resolve())
    df = _loaded_dfs.get(resolved)
    if df is None:
        try:
            df = pd.read_csv(resolved)
            _loaded_dfs[resolved] = df
        except Exception as e:
            return {"error": f"Cannot read file: {e}"}
    info = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        nulls = int(df[col].isnull().sum())
        info.append({"column": col, "dtype": dtype, "nulls": nulls})
    return {"rows": len(df), "columns": len(df.columns), "schema": info}


@mcp.tool()
def query_csv(file_path: str, column: str = "", operation: str = "describe") -> dict:
    resolved = str(Path(file_path.strip()).resolve())
    df = _loaded_dfs.get(resolved)
    if df is None:
        try:
            df = pd.read_csv(resolved)
            _loaded_dfs[resolved] = df
        except Exception as e:
            return {"error": f"Cannot read file: {e}"}
    if column and column not in df.columns:
        return {"error": f"Column '{column}' not found."}
    try:
        if operation == "describe":
            if column:
                return df[column].describe().to_dict()
            return df.describe().to_dict()
        elif operation == "value_counts":
            return df[column].value_counts().head(20).to_dict()
        elif operation == "top_correlations":
            corr = df.corr(numeric_only=True)
            if column:
                return corr[column].sort_values(ascending=False).head(10).to_dict()
            return {}
        elif operation == "missing":
            if column:
                return {"column": column, "missing": int(df[column].isnull().sum())}
            return df.isnull().sum().to_dict()
        elif operation == "sample":
            return df.head(5).to_dict(orient="records")
        return {"error": f"Unknown operation: {operation}"}
    except Exception as e:
        return {"error": str(e)}


def _load_or_get(path: str) -> pd.DataFrame:
    resolved = str(Path(path.strip()).resolve())
    if resolved not in _loaded_dfs:
        _loaded_dfs[resolved] = pd.read_csv(resolved)
    return _loaded_dfs[resolved]


@mcp.tool()
def compare_datasets(path_a: str, path_b: str) -> dict:
    try:
        df_a = _load_or_get(path_a)
        df_b = _load_or_get(path_b)
    except Exception as e:
        return {"status": "error", "error": str(e)}

    cols_a, cols_b = set(df_a.columns), set(df_b.columns)
    shared = cols_a & cols_b
    only_a = cols_a - cols_b
    only_b = cols_b - cols_a

    result = {
        "file_a": {"path": path_a, "rows": len(df_a), "columns": len(df_a.columns)},
        "file_b": {"path": path_b, "rows": len(df_b), "columns": len(df_b.columns)},
        "shared_columns": len(shared),
        "columns_only_in_a": list(only_a),
        "columns_only_in_b": list(only_b),
        "dtype_mismatches": [],
        "missing_values": {},
        "numeric_stats": {},
    }

    for col in sorted(shared):
        dtype_a, dtype_b = df_a[col].dtype, df_b[col].dtype
        if dtype_a != dtype_b:
            result["dtype_mismatches"].append({"column": col, "dtype_a": str(dtype_a), "dtype_b": str(dtype_b)})
        result["missing_values"][col] = {"a": int(df_a[col].isnull().sum()), "b": int(df_b[col].isnull().sum())}
        if pd.api.types.is_numeric_dtype(dtype_a) and pd.api.types.is_numeric_dtype(dtype_b):
            a_s, b_s = df_a[col].dropna(), df_b[col].dropna()
            if len(a_s) and len(b_s):
                result["numeric_stats"][col] = {
                    "a_mean": round(float(a_s.mean()), 2),
                    "b_mean": round(float(b_s.mean()), 2),
                    "a_std": round(float(a_s.std()), 2),
                    "b_std": round(float(b_s.std()), 2),
                    "a_min": round(float(a_s.min()), 2),
                    "b_min": round(float(b_s.min()), 2),
                    "a_max": round(float(a_s.max()), 2),
                    "b_max": round(float(b_s.max()), 2),
                }

    return result


@mcp.tool()
def read_file(file_path: str) -> dict:
    """Read the full contents of any text file on disk.
    Useful for viewing data descriptions, README files, or
    non-CSV context files.
    """
    resolved = str(Path(file_path.strip()).resolve())
    try:
        with open(resolved, "r") as f:
            content = f.read()
        return {"status": "success", "path": resolved, "content": content}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@mcp.tool()
def deploy_to_cloud_run(
    project_id: str,
    region: str = "us-central1",
    service_name: str = "ai-analytics-dept",
    gemini_api_key: str = "",
) -> dict:
    """Build and deploy this application to Google Cloud Run.

    Uses Cloud Build to containerize the source (no local Docker needed)
    then deploys the image to Cloud Run.

    Prerequisites:
    - A GCP project with billing enabled
    - Cloud Run, Cloud Build, and Artifact Registry APIs enabled
    - Application Default Credentials configured (gcloud auth application-default login)
    - GEMINI_API_KEY provided or set as environment variable

    Args:
        project_id: Your GCP project ID.
        region: Cloud Run region (default: us-central1).
        service_name: Cloud Run service name (default: ai-analytics-dept).
        gemini_api_key: Gemini API key for the deployed service (falls back to GEMINI_API_KEY env var).
    """
    import os
    import tarfile
    import io
    import time
    from pathlib import Path

    api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return {
            "status": "error",
            "error": "GEMINI_API_KEY not provided. Pass gemini_api_key or set the GEMINI_API_KEY environment variable.",
        }

    project_root = Path(__file__).resolve().parent.parent
    image_uri = f"{region}-docker.pkg.dev/{project_id}/cloud-run-source-deploy/{service_name}"

    # --- Step 1: Package source into a tarball ---
    try:
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for path in project_root.rglob("*"):
                rel = path.relative_to(project_root)
                parts = rel.parts
                if any(p.startswith(".") for p in parts):
                    continue
                if any(
                    p in ("__pycache__", ".venv", "node_modules", "local_logs", "logs", "outputs")
                    for p in parts
                ):
                    continue
                if path.is_file():
                    tar.add(path, arcname=rel)
        buf.seek(0)
    except Exception as e:
        return {"status": "error", "error": f"Failed to package source: {e}"}

    # --- Step 2: Upload source tarball to Cloud Build's staging bucket ---
    try:
        from google.cloud import storage
        from google.api_core.exceptions import NotFound

        storage_client = storage.Client(project=project_id)
        bucket_name = f"{project_id}_cloudbuild"
        try:
            bucket = storage_client.get_bucket(bucket_name)
        except NotFound:
            bucket = storage_client.create_bucket(bucket_name, location=region)

        blob_name = f"source/{int(time.time())}-{service_name}.tar.gz"
        blob = bucket.blob(blob_name)
        blob.upload_from_file(buf, content_type="application/gzip")
    except Exception as e:
        return {"status": "error", "error": f"Failed to upload source to GCS: {e}"}

    # --- Step 3: Submit Cloud Build to create the Docker image ---
    try:
        from google.cloud.devtools.cloudbuild_v1 import CloudBuildClient

        build_client = CloudBuildClient()
        build = {
            "source": {
                "storage_source": {
                    "bucket": bucket_name,
                    "object": blob_name,
                },
            },
            "steps": [
                {
                    "name": "gcr.io/cloud-builders/docker",
                    "args": ["build", "-t", image_uri, "."],
                },
            ],
            "images": [image_uri],
            "timeout": "600s",
        }
        op = build_client.create_build(project_id=project_id, build=build)
        op.result(timeout=600)
    except Exception as e:
        return {"status": "error", "error": f"Cloud Build failed: {e}"}

    # --- Step 4: Deploy the image to Cloud Run ---
    try:
        from google.cloud.run_v2 import ServicesClient
        from google.cloud.run_v2.types import Service, RevisionTemplate, Container, EnvVar
        from google.api_core.exceptions import NotFound

        run_client = ServicesClient()
        parent = f"projects/{project_id}/locations/{region}"
        service_full = f"{parent}/services/{service_name}"

        service_config = Service(
            template=RevisionTemplate(
                containers=[
                    Container(
                        image=image_uri,
                        env=[
                            EnvVar(name="GEMINI_API_KEY", value=api_key),
                            EnvVar(name="PYTHONUNBUFFERED", value="1"),
                        ],
                        resources={"limits": {"memory": "2048Mi", "cpu": "2"}},
                    )
                ],
                timeout="300s",
            ),
        )

        try:
            run_client.get_service(name=service_full)
            op2 = run_client.update_service(service={"name": service_full, "template": service_config.template})
        except NotFound:
            op2 = run_client.create_service(parent=parent, service=service_config, service_id=service_name)

        op2.result(timeout=300)
        deployed = run_client.get_service(name=service_full)
        service_url = getattr(deployed, "uri", None) or f"https://{service_name}-xxxxx-{region}.a.run.app"
    except Exception as e:
        return {"status": "error", "error": f"Cloud Run deployment failed: {e}"}

    return {
        "status": "success",
        "service_url": service_url,
        "service_name": service_name,
        "region": region,
        "project_id": project_id,
        "image": image_uri,
    }


def main():
    import asyncio
    asyncio.run(mcp.run_stdio_async())


if __name__ == "__main__":
    main()
