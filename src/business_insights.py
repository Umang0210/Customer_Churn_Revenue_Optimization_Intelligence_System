import os
import json
import joblib
import pandas as pd

# -----------------------------
# CONFIG
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "../data/processed/customer_features.csv")
MODEL_PATH = os.path.join(BASE_DIR, "../models/churn_model.pkl")
FEATURES_PATH = os.path.join(BASE_DIR, "../models/feature_list.json")

# -----------------------------
# LOAD ASSETS
# -----------------------------
if not os.path.exists(DATA_PATH):
    raise FileNotFoundError(f"Data not found at {DATA_PATH}")

df = pd.read_csv(DATA_PATH)
model = joblib.load(MODEL_PATH)

with open(FEATURES_PATH, "r") as f:
    features = json.load(f)

# -----------------------------
# PREPROCESSING
# -----------------------------
# 1. Schema Normalization (Match train.py)
df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

# 2. Encoding
# We need to replicate encoding to match model features.
# Since we don't have the original encoder logic saved, we rely on pandas 
# but must align with 'features' list.
CATEGORICAL_COLS = ["gender", "seniorcitizen", "contract"]
X_encoded = pd.get_dummies(df, columns=CATEGORICAL_COLS, drop_first=True)

# 3. Align Columns
# Ensure X has exactly the same columns as the model expects
X = X_encoded.reindex(columns=features, fill_value=0)

# -----------------------------
# PREDICTION & INSIGHTS
# -----------------------------
df["churn_probability"] = model.predict_proba(X)[:, 1]

# Revenue calculation (assuming standard column names after normalization)
# train.py normalized these to: 'monthlycharges', 'tenure'
df["revenue"] = df["monthlycharges"] * df["tenure"]
df["expected_revenue_loss"] = df["churn_probability"] * df["revenue"]
df["priority_score"] = df["expected_revenue_loss"]

summary = {
    "total_customers": len(df),
    "churn_rate": round(df["churn"].map({'yes': 1, 'no': 0}).mean() * 100, 2), # Handle yes/no if present
    "high_risk_pct": round((df["churn_probability"] > 0.7).mean() * 100, 2),
    "total_revenue": round(df["revenue"].sum(), 2),
    "revenue_at_risk": round(df["expected_revenue_loss"].sum(), 2)
}

print("\n📊 Business Insights Summary:")
print(json.dumps(summary, indent=4))

# Optional: Top risky customers
print("\n🔥 Top 5 High Risk & High Value Customers:")
print(df.sort_values("priority_score", ascending=False)
      [["customerid", "churn_probability", "expected_revenue_loss"]]
      .head(5)
      .to_string(index=False))
