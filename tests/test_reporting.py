# test_reporting.py

import json

# pyrefly: ignore [missing-import]
from tools.reporting import generate_report

result = generate_report(
    "data/raw/house-prices-advanced-regression-techniques/train.csv"
)

print(json.dumps(result, indent=4))
