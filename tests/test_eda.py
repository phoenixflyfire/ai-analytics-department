import json
from tools.eda import run_eda

result = run_eda()

print(json.dumps(result, indent=4))
