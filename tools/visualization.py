import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
from ai_analytics_department.schemas.shared_data import data_container

# Define the output directory using an absolute path to be robust
# This ensures charts are saved correctly regardless of the execution directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHARTS_DIR = PROJECT_ROOT / "outputs" / "charts"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

def create_saleprice_distribution(column: str | None = None) -> dict:
    if data_container.df.empty:
        return {"error": "Data not loaded. Please run the data engineer first."}

    df = data_container.df
    numeric_cols = df.select_dtypes(include=["number"]).columns
    target = column if column and column in df.columns else (numeric_cols[-1] if len(numeric_cols) else df.columns[0])

    plt.figure(figsize=(8, 5))
    plt.hist(df[target].dropna().tolist(), bins=30)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = CHARTS_DIR / f"distribution_{target}_{ts}.png"

    plt.title(f"{target} Distribution")
    plt.xlabel(target)
    plt.ylabel("Frequency")

    plt.savefig(output_file)
    plt.close()
    print(f"📊 Chart saved: {output_file}")

    return {
        "chart": str(output_file)
    }

def create_correlation_chart(column: str | None = None) -> dict:
    if data_container.df.empty:
        return {"error": "Data not loaded. Please run the data engineer first."}

    df = data_container.df
    numeric_cols = df.select_dtypes(include=["number"]).columns
    if len(numeric_cols) < 2:
        return {"error": "Need at least 2 numeric columns for correlation."}
    target = column if column and column in df.columns else numeric_cols[-1]

    correlations = (
        df.corr(numeric_only=True)[target]
        .sort_values(ascending=False)
        .head(10)
    )

    plt.figure(figsize=(10, 5))
    correlations.plot(kind="bar")

    plt.title(f"Top Correlations With {target}")
    plt.ylabel("Correlation")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = CHARTS_DIR / f"top_correlations_{target}_{ts}.png"

    plt.tight_layout()
    plt.savefig(output_file)
    plt.close()
    print(f"📊 Chart saved: {output_file}")

    return {
        "chart": str(output_file)
    }