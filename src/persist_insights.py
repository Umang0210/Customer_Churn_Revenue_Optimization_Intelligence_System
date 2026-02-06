import json
import joblib
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine


# -----------------------------
# CONFIG
# -----------------------------
DB_URI = "mysql+pymysql://username:password@localhost:3306/churn_intelligence"

DATA_PATH = "data/processed/customer_features.csv"
MODEL_PATH = "models/churn_model.pkl"
FEATURES_PATH = "models/feature_list.json"
METADATA_PATH = "models/model_metadata.json"


# -----------------------------
# DB CONNECTION
# -----------------------------
engine = create_engine(DB_URI)


# -----------------------------
# LOAD DATA & ARTIFACTS
# -----------------------------
df = pd.read_csv(DATA_PATH)

df.columns = (
    df.columns
    .str.strip()
    .str.lower()
    .str.replace(" ", "_")
)

model = joblib.load(MODEL_PATH)

with open(FEATURES_PATH) as f:
    feature_list = json.load(f)

with open(METADATA_PATH) as f:
    metadata = json.load(f)

model_version = metadata["model_version"]
timestamp = datetime.utcnow()


# -----------------------------
# PREDICTIONS
# -----------------------------
X = df[feature_list]
df["churn_probability"] = model.predict_proba(X)[:, 1]

df["risk_bucket"] = pd.cut(
    df["churn_probability"],
    bins=[0, 0.4, 0.7, 1.0],
    labels=["LOW", "MEDIUM", "HIGH"]
)


# -----------------------------
# BUSINESS METRICS
# -----------------------------
df["revenue"] = df["monthlycharges"] * df["tenure"]
df["expected_revenue_loss"] = df["churn_probability"] * df["revenue"]
df["priority_score"] = df["expected_revenue_loss"]


# -----------------------------
# TABLE 1: CUSTOMER PREDICTIONS
# -----------------------------
customer_predictions = df[[
    "customerid",
    "churn_probability",
    "risk_bucket",
    "revenue",
    "expected_revenue_loss",
    "priority_score"
]].copy()

customer_predictions.rename(
    columns={"customerid": "customer_id"},
    inplace=True
)

customer_predictions["model_version"] = model_version
customer_predictions["prediction_timestamp"] = timestamp

customer_predictions.to_sql(
    "customers_predictions",
    engine,
    if_exists="replace",
    index=False
)


# -----------------------------
# TABLE 2: BUSINESS KPIs
# -----------------------------
kpis = pd.DataFrame([
    ("total_customers", len(df)),
    ("churn_rate_pct", round(df["churn"].mean() * 100, 2)),
    ("high_risk_pct", round((df["risk_bucket"] == "HIGH").mean() * 100, 2)),
    ("total_revenue", round(df["revenue"].sum(), 2)),
    ("revenue_at_risk", round(df["expected_revenue_loss"].sum(), 2))
], columns=["metric_name", "metric_value"])

kpis["generated_at"] = timestamp

kpis.to_sql(
    "business_kpis",
    engine,
    if_exists="replace",
    index=False
)


# -----------------------------
# TABLE 3: SEGMENT INSIGHTS
# -----------------------------
segment_contract = (
    df.groupby("contract")
      .agg(
          churn_rate=("churn", "mean"),
          customer_count=("customerid", "count")
      )
      .reset_index()
)

segment_contract["segment_type"] = "contract"
segment_contract["generated_at"] = timestamp
segment_contract.rename(columns={"contract": "segment_value"}, inplace=True)

segment_contract.to_sql(
    "segment_insights",
    engine,
    if_exists="replace",
    index=False
)


# -----------------------------
# TABLE 4: MODEL RUN METRICS
# -----------------------------
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


print("✅ Insights and predictions successfully persisted to MySQL")
