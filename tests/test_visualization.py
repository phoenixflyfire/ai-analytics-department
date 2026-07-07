# test_visualization.py

# pyrefly: ignore [missing-import]
from tools.visualization import create_saleprice_distribution

result1 = create_saleprice_distribution(
    "data/raw/house-prices-advanced-regression-techniques/train.csv"
)

print(result1)

# pyrefly: ignore [missing-import]
from tools.visualization import create_correlation_chart

result2 = create_correlation_chart(
    "data/raw/house-prices-advanced-regression-techniques/train.csv"
)

print(result2)
