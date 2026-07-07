import pandas as pd


class DataContainer:
    def __init__(self):
        self.df: pd.DataFrame = pd.DataFrame()
        self.raw_data: dict | None = None
        self.pipeline_complete: bool = False
        self.current_csv_path: str | None = None
        self.pipeline_cycle: int = 0
        self.diagnostic_mode: bool = True


data_container = DataContainer()
