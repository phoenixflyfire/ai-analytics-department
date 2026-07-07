# ==========================================================
# ai_analytics_department/tools/data_loader.py
# ==========================================================
# ==========================================================
# This file is merged with adapter.py
# ==========================================================

import csv
from pathlib import Path
from ai_analytics_department.schemas.schemas import AdapterInput

def csv_to_rawdata_adapter_node(input_data: AdapterInput) -> dict:
    """Standard Python function that reads CSV data.
    
    Returns a pure serializable dictionary for ADK safety.
    """
    # 1. Clean the extracted file path string
    target_path = input_data.file_path.strip()
    
    # FIXED: Expression parse error cleared by assigning a valid empty list value
    if target_path == "dummy":
        return {"status": "success", "raw_records": []}
        
    # 2. Resilient implementation using the EAFP principle
    try:
        file_path_obj = Path(target_path)
        
        # Verify if the target file actually exists on local disk
        if not file_path_obj.exists():
            print(f"⚠️ [Adapter] File does not exist on disk: {file_path_obj.resolve()}")
            return {
                "status": "failed",
                "error": f"File path not found: {target_path}",
                "raw_records": []  # Safe list prevents upstream pipeline crashes
            }

        # Attempt to read the CSV content stream cleanly
        with open(file_path_obj, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            records = list(reader)[:5]  # Slice first 5 rows to prevent token context bloat loops
            
            return {
                "status": "success", 
                "raw_records": records
            }
            
    except Exception as e:
        # Forgiveness: Catch file lock or encoding bugs gracefully to keep workflow moving
        print(f"❌ [Adapter] Critical error reading CSV dataset: {e}")
        return {
            "status": "failed",
            "error": str(e),
            "raw_records": []
        }


import json
import pandas as pd
from ai_analytics_department.schemas.schemas import RawData
from ai_analytics_department.schemas.shared_data import data_container # New import

def load_dataset(file_path: str) -> RawData:
    """
    SOLUTION 5 ROOT-LEVEL IMPLEMENTATION: Normalizes and unifies tool 
    execution output layout parameters for seamless multi-agent consumption.
    """
    print(f"📥 [Tool Execution] Loading target CSV file data stream from: {file_path}")
    
    try:
        df = pd.read_csv(file_path)
        data_container.df = df
        rows = len(df)
        columns = len(df.columns)
    except Exception as e:
        print(f"⚠️ [Tool Execution] File reading failed: {e}")
        data_container.raw_data = {"status": "ERROR", "error": str(e)}
        return RawData(
            data_content=json.dumps({"status": "ERROR", "error": str(e)}),
            source="loaded_from_csv"
        )

    # TRUE SOLUTION 5 CODE: Pack the exact same schema structure layout shape as run_eda!
    # Both tools now speak the exact same data vocabulary to prevent context confusion loops.
    unified_envelope = {
        "status": "SUCCESS",
        "rows": rows,
        "columns": columns,
        "source": "loaded_from_csv"
    }
    
    print(f"✅ [Tool Execution] Dataset successfully indexed: {unified_envelope}")
    return RawData(
        data_content=json.dumps(unified_envelope),
        source="loaded_from_csv"
    )
