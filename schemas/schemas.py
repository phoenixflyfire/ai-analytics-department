from pydantic import BaseModel
from typing import Any, Optional


class RawData(BaseModel):
    data_content: str
    source: str = "unknown"


class AdapterInput(BaseModel):
    file_path: str


class DataEngineerStatus(BaseModel):
    status: str
