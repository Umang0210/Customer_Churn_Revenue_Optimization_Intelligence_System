import os
import glob
import pandas as pd

PROCESSED_DATA_DIR = "data/processed"
CLEAN_DATA_PATH = os.path.join(PROCESSED_DATA_DIR, "clean_customers.csv")


def get_latest_raw_snapshot():
    files = glob.glob(os.path.join(PROCESSED_DATA_DIR, "raw_snapshot_*.csv"))
    if not files:
        raise FileNotFoundError("No raw snapshot found. Run ingestion.py first.")
    return max(files, key=os.path.getctime)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    # 1. Standardize column names
    df.columns = df.columns.str.strip().str.lower()

    # 2. Remove duplicate rows
    df = df.drop_duplicates()

    # 3. Convert numeric columns safely
    numeric_cols = [
        "monthlycharges",
        "totalcharges",
        "tenure"
    ]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 4. Handle missing values
    df = df.dropna(subset=["churn"])  # target must exist

    df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())

    # 5. Normalize categorical columns
    categorical_cols = df.select_dtypes(include="object").columns

    for col in categorical_cols:
        df[col] = df[col].str.strip().str.lower()

    # 6. Remove logically invalid rows
    if "tenure" in df.columns:
        df = df[df["tenure"] >= 0]

    if "monthlycharges" in df.columns:
        df = df[df["monthlycharges"] >= 0]

    return df


def run_cleaning():
    input_path = get_latest_raw_snapshot()
    print(f"Cleaning data from: {input_path}")

    df = pd.read_csv(input_path)

    cleaned_df = clean_data(df)

    cleaned_df.to_csv(CLEAN_DATA_PATH, index=False)

    print(f"Cleaned data saved to: {CLEAN_DATA_PATH}")
    print(f"Final shape: {cleaned_df.shape}")


if __name__ == "__main__":
    run_cleaning()