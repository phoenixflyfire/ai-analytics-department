import json

# pyrefly: ignore [missing-import]
from tools.reporting import generate_report


DATASET_PATH = (
    "data/raw/house-prices-advanced-regression-techniques/train.csv"
)

result = generate_report(DATASET_PATH)

print(json.dumps(result, indent=4))
