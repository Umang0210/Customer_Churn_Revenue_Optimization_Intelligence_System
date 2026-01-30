import os
import pandas as pd
from datetime import datetime

RAW_DATA_DIR = "data/raw"
PROCESSED_DATA_DIR = "data/processed"

REAL_DATA_FILE = "WA_Fn-UseC_-Telco-Customer-Churn.csv"
SAMPLE_DATA_FILE = "Sample_dataset.csv"


def get_input_file():
    """
    Prefer real dataset if available, otherwise use sample dataset.
    """
    real_path = os.path.join(RAW_DATA_DIR, REAL_DATA_FILE)
    sample_path = os.path.join(RAW_DATA_DIR, SAMPLE_DATA_FILE)

    if os.path.exists(real_path):
        print("Using REAL dataset")
        return real_path
    elif os.path.exists(sample_path):
        print("Using SAMPLE dataset")
        return sample_path
    else:
        raise FileNotFoundError("No dataset found in data/raw/")


def ingest_data():
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)

    input_file = get_input_file()

    df = pd.read_csv(input_file)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"raw_snapshot_{timestamp}.csv"
    output_path = os.path.join(PROCESSED_DATA_DIR, output_file)

    df.to_csv(output_path, index=False)

    print(f"Raw data snapshot saved to: {output_path}")
    print(f"Rows: {df.shape[0]}, Columns: {df.shape[1]}")


if __name__ == "__main__":
    ingest_data()
