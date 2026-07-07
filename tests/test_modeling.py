# test_modelling.py

import json


from tools.modeling import train_house_price_model

result = train_house_price_model()

print(json.dumps(result, indent=4))
