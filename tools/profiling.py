import pandas as pd
from ai_analytics_department.schemas.shared_data import data_container


def profile_dataset() -> dict:
    """
    Profiles the dataset from the shared data container.
    """
    if data_container.df.empty:
        return {"error": "Data not loaded. Please run the data engineer first."}

    df = data_container.df

    missing_values = (
        df.isnull()
        .sum()
        .sort_values(ascending=False)
    )

    missing_values = {
        col: int(count)
        for col, count in missing_values.items()
        if count > 0
    }

    return {
        "rows": len(df),
        "columns": len(df.columns),
        "numeric_columns": len(
            df.select_dtypes(include="number")
        ),
        "categorical_columns": len(
            df.select_dtypes(include="object")
        ),
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_values": missing_values,
        "target_column": "SalePrice"
    }