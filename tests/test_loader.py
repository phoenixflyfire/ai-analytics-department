# import from load_dataset function
import json
# pyrefly: ignore [missing-import]
from tools.data_loader import load_dataset

result = load_dataset("data/raw/house-prices-advanced-regression-techniques/train.csv")

print(json.dumps(result, indent=4))
