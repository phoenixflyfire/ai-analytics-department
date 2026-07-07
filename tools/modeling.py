# ==========================================================
# ai_analytics_department/tools/modeling.py
# ==========================================================

from typing import Any, Dict
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score
from ai_analytics_department.schemas.shared_data import data_container


def _get_target_column(df: pd.DataFrame, preferred: str | None = None) -> str | None:
    numeric = df.select_dtypes(include=["number"])
    if numeric.empty:
        return None
    if preferred and preferred in numeric.columns:
        return preferred
    return numeric.columns[-1]


def train_house_price_model(ctx: Any = None, target_column: str | None = None) -> Dict[str, Any]:
    if data_container.df.empty:
        return {
            "status": "ERROR",
            "error": "No data loaded. Run the data engineer first.",
        }

    df = data_container.df
    rows = len(df)
    columns = len(df.columns)

    target_col = _get_target_column(df, target_column)
    if target_col is None:
        return {
            "status": "ERROR",
            "error": "No numeric columns found for training.",
        }

    numeric_df = df.select_dtypes(include=["number"]).dropna()
    if len(numeric_df) < 10:
        return {
            "status": "ERROR",
            "error": "Too few samples after dropping missing values.",
        }

    X = numeric_df.drop(columns=[target_col])
    y = numeric_df[target_col]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    score = r2_score(y_test, y_pred)

    return {
        "status": "SUCCESS",
        "r_squared": round(score, 4),
        "model_type": "RandomForestRegressor",
        "training_samples": int(rows),
        "features_processed": int(columns),
        "target_column": target_col,
    }
