import pandas as pd
from ai_analytics_department.schemas.shared_data import data_container


def get_schema() -> dict:
    if data_container.df.empty:
        return {"error": "No data loaded."}
    info = []
    for col in data_container.df.columns:
        dtype = str(data_container.df[col].dtype)
        nulls = int(data_container.df[col].isnull().sum())
        info.append({"column": col, "dtype": dtype, "nulls": nulls})
    return {
        "rows": len(data_container.df),
        "columns": len(data_container.df.columns),
        "schema": info,
    }


def query_df(column: str = "", operation: str = "describe") -> dict:
    if data_container.df.empty:
        return {"error": "No data loaded."}
    df = data_container.df
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
