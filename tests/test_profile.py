import json
# pyrefly: ignore [missing-import]
from tools.profiling import profile_dataset


result = profile_dataset(
    "data/raw/house-prices-advanced-regression-techniques/train.csv"
)

print(json.dumps(result, indent=4))
