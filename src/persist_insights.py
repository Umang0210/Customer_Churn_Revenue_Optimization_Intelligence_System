import json
import joblib
import pandas as pd
from datetime import datetime, timezone
from sqlalchemy import create_engine


# =====================================================
# CONFIG
# =====================================================
DB_URI = "mysql+pymysql://churn_user:StrongPassword123@localhost:3306/churn_intelligence"

DATA_PATH = "data/processed/customer_features.csv"
MODEL_PATH = "models/churn_model.pkl"
FEATURES_PATH = "models/feature_list.json"
METADATA_PATH = "models/model_metadata.json"


# =====================================================
# DATABASE CONNECTION
# =====================================================
engine = create_engine(DB_URI)


# =====================================================
# LOAD DATA
# =====================================================
df = pd.read_csv(DATA_PATH)

# Normalize column names (must match training)
df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)


# =====================================================
# NORMALIZE TARGET COLUMN (CRITICAL FIX)
# =====================================================
df["churn"] = (
    df["churn"]
    .astype(str)
    .str.strip()
    .str.lower()
    .map({"yes": 1, "no": 0})
)

if df["churn"].isnull().any():
    raise ValueError("Invalid values found in churn column after normalization")


# =====================================================
# LOAD MODEL & METADATA
# =====================================================
model = joblib.load(MODEL_PATH)

with open(FEATURES_PATH, "r") as f:
    feature_list = json.load(f)

with open(METADATA_PATH, "r") as f:
    metadata = json.load(f)

model_version = metadata["model_version"]
timestamp = datetime.now(timezone.utc)


# =====================================================
# PREPROCESSING (IDENTICAL TO TRAINING)
# =====================================================
NUMERIC_COLS = [
    "tenure",
    "monthlycharges",
    "totalcharges"
]

CATEGORICAL_COLS = [
    "gender",
    "seniorcitizen",
    "contract"
]

# Raw features
X_raw = df[NUMERIC_COLS + CATEGORICAL_COLS]

# One-hot encode categoricals
X_encoded = pd.get_dummies(
    X_raw,
    columns=CATEGORICAL_COLS,
    drop_first=True
)

# Align inference features with training schema
for col in feature_list:
    if col not in X_encoded.columns:
        X_encoded[col] = 0

X_final = X_encoded[feature_list]


# =====================================================
# GENERATE PREDICTIONS
# =====================================================
df["churn_probability"] = model.predict_proba(X_final)[:, 1]

df["risk_bucket"] = pd.cut(
    df["churn_probability"],
    bins=[0.0, 0.4, 0.7, 1.0],
    labels=["LOW", "MEDIUM", "HIGH"]
)


# =====================================================
# BUSINESS METRICS
# =====================================================
df["revenue"] = df["monthlycharges"] * df["tenure"]
df["expected_revenue_loss"] = df["churn_probability"] * df["revenue"]
df["priority_score"] = df["expected_revenue_loss"]


# =====================================================
# TABLE 1: CUSTOMER PREDICTIONS
# =====================================================
customers_predictions = df[[
    "customerid",
    "churn_probability",
    "risk_bucket",
    "revenue",
    "expected_revenue_loss",
    "priority_score"
]].copy()

customers_predictions.rename(
    columns={"customerid": "customer_id"},
    inplace=True
)

customers_predictions["model_version"] = model_version
customers_predictions["prediction_timestamp"] = timestamp

customers_predictions.to_sql(
    "customers_predictions",
    engine,
    if_exists="replace",
    index=False
)


# =====================================================
# TABLE 2: BUSINESS KPIs
# =====================================================
business_kpis = pd.DataFrame([
    ("total_customers", len(df)),
    ("churn_rate_pct", round(df["churn"].mean() * 100, 2)),
    ("high_risk_pct", round((df["risk_bucket"] == "HIGH").mean() * 100, 2)),
    ("total_revenue", round(df["revenue"].sum(), 2)),
    ("revenue_at_risk", round(df["expected_revenue_loss"].sum(), 2))
], columns=["metric_name", "metric_value"])

business_kpis["generated_at"] = timestamp

business_kpis.to_sql(
    "business_kpis",
    engine,
    if_exists="replace",
    index=False
)


# =====================================================
# TABLE 3: SEGMENT INSIGHTS
# =====================================================
segment_insights = (
    df.groupby("contract")
      .agg(
          churn_rate=("churn", "mean"),
          customer_count=("customerid", "count")
      )
      .reset_index()
)

segment_insights.rename(columns={"contract": "segment_value"}, inplace=True)
segment_insights["segment_type"] = "contract"
segment_insights["generated_at"] = timestamp

segment_insights.to_sql(
    "segment_insights",
    engine,
    if_exists="replace",
    index=False
)


# =====================================================
# TABLE 4: MODEL RUN METRICS (GOVERNANCE)
# =====================================================
model_run = pd.DataFrame([{
    "model_version": model_version,
    "roc_auc": metadata["final_model_metrics"]["roc_auc"],
    "precision_score": metadata["final_model_metrics"]["precision"],
    "recall_score": metadata["final_model_metrics"]["recall"],
    "training_rows": metadata["training_rows"],
    "run_timestamp": timestamp
}])

model_run.to_sql(
    "model_runs",
    engine,
    if_exists="append",
    index=False
)


print("✅ persist_insights.py completed successfully")
print("✅ MySQL tables populated:")
print("✅ Customers_predictions")
print("✅ Business_kpis")
print("✅ Segment_insights")
print("✅ Model_runs")
