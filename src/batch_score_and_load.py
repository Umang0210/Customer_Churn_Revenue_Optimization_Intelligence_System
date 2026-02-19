import pandas as pd
import joblib
import json
import mysql.connector
from pathlib import Path
from datetime import date

# ===============================
# Paths
# ===============================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "processed" / "final_dataset.csv"
MODEL_DIR = BASE_DIR / "models"

# ===============================
# Load assets
# ===============================
model = joblib.load(MODEL_DIR / "churn_model.pkl")

try:
    scaler = joblib.load(MODEL_DIR / "scaler.pkl")
except FileNotFoundError:
    scaler = None

with open(MODEL_DIR / "feature_list.json") as f:
    feature_list = json.load(f)

# ===============================
# DB connection
# ===============================
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="churn_user",
        password="StrongPassword123",
        database="churn_intelligence"
    )

# ===============================
# Helper functions
# ===============================
def read_processed_data():
    df = pd.read_csv(DATA_PATH)
    df.columns = df.columns.str.lower()
    return df

def transform_features(df):
    X = df.copy()
    X = X.reindex(columns=feature_list, fill_value=0)
    return scaler.transform(X) if scaler else X

def map_risk(prob):
    if prob >= 0.7:
        return "HIGH"
    elif prob >= 0.4:
        return "MEDIUM"
    return "LOW"

def write_df_to_mysql(df):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Ensure customer_id column exists
    if "customer_id" not in df.columns:
        if "customerid" in df.columns:
            df["customer_id"] = df["customerid"]
        else:
            # Create customer_id from index if not available
            df["customer_id"] = df.index + 1
            print("Warning: No customer_id column found, using index as customer_id")

    query = """
        INSERT INTO customer_churn_analytics (
            customer_id,
            churn_probability,
            risk_bucket,
            revenue,
            expected_revenue_loss,
            priority_score,
            model_version,
            batch_run_date
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    for _, row in df.iterrows():
        cursor.execute(query, (
            row["customer_id"],
            float(row["churn_probability"]),
            row["risk_bucket"],
            float(row["revenue"]),
            float(row["expected_revenue_loss"]),
            float(row["priority_score"]),
            "v1.0",
            date.today()
        ))

    conn.commit()
    cursor.close()
    conn.close()

# ===============================
# MAIN PIPELINE
# ===============================
def main():
    print("Loading processed data...")
    df = read_processed_data()

    print("Transforming features...")
    X = transform_features(df)

    print("Running predictions...")
    probs = model.predict_proba(X)[:, 1]

    df["churn_probability"] = probs
    df["risk_bucket"] = df["churn_probability"].apply(map_risk)
    
    # Ensure revenue column exists
    if "revenue" not in df.columns:
        if "monthlycharges" in df.columns:
            df["revenue"] = df["monthlycharges"]
        else:
            df["revenue"] = 0
            print("Warning: No revenue data available, using 0 as default")
    
    df["expected_revenue_loss"] = df["churn_probability"] * df["revenue"]
    df["priority_score"] = df["expected_revenue_loss"] * df["churn_probability"]

    print("Writing to MySQL...")
    write_df_to_mysql(df)

    print("Batch scoring completed successfully.")

if __name__ == "__main__":
    main()