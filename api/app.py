from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import joblib
import pandas as pd
import json
import mysql.connector
from pathlib import Path

# ===============================
# App Init
# ===============================
app = FastAPI(
    title="Churn Intelligence API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# Paths
# ===============================
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models"

# ===============================
# Load ML Assets
# ===============================
try:
    model = joblib.load(MODEL_DIR / "churn_model.pkl")
except Exception as e:
    raise RuntimeError(f"Failed to load model: {e}")

try:
    scaler = joblib.load(MODEL_DIR / "scaler.pkl")
except FileNotFoundError:
    scaler = None

try:
    with open(MODEL_DIR / "feature_list.json") as f:
        feature_list = json.load(f)
except FileNotFoundError:
    feature_list = []

# ===============================
# Database
# ===============================
def get_db_connection():
    try:
        return mysql.connector.connect(
            host="localhost",
            user="churn_user",
            password="StrongPassword123",
            database="churn_intelligence"
        )
    except mysql.connector.Error as e:
        raise HTTPException(status_code=500, detail=str(e))

def insert_prediction(**kwargs):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO customers_predictions (
            customer_id,
            churn_probability,
            risk_bucket,
            revenue,
            expected_revenue_loss,
            priority_score,
            model_version
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    cursor.execute(query, (
        kwargs["customer_id"],
        kwargs["churn_probability"],
        kwargs["risk_bucket"],
        kwargs["revenue"],
        kwargs["expected_revenue_loss"],
        kwargs["priority_score"],
        kwargs["model_version"]
    ))

    conn.commit()
    cursor.close()
    conn.close()

# ===============================
# Request Schema
# ===============================
class ChurnRequest(BaseModel):
    customer_id: str
    revenue: float
    monthly_charges: float
    usage_frequency: int
    complaints_count: int
    payment_delays: int
    gender: str = "missing"
    seniorcitizen: str = "missing"
    contract: str = "missing"

# ===============================
# Health
# ===============================
@app.get("/health")
def health():
    return {"status": "ok"}

# ===============================
# Predict (FINAL CONTRACT)
# ===============================
@app.post("/predict")
def predict(request: ChurnRequest):

    df = pd.DataFrame([request.dict()])
    df.columns = df.columns.str.lower()

    categorical_cols = ["gender", "seniorcitizen", "contract"]
    df_encoded = pd.get_dummies(df, columns=categorical_cols, drop_first=True)

    if feature_list:
        df_final = df_encoded.reindex(columns=feature_list, fill_value=0)
    else:
        df_final = df_encoded

    X = scaler.transform(df_final) if scaler else df_final
    prob = float(model.predict_proba(X)[0][1])

    if prob >= 0.7:
        risk = "HIGH"
    elif prob >= 0.4:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    # -------------------------------
    # Action Logic
    # -------------------------------
    if prob >= 0.7:
        action = "RETENTION_CALL"
        urgency = "IMMEDIATE"
        confidence = "HIGH"
        reason = "High churn risk with significant revenue exposure"
    elif prob >= 0.4:
        action = "DISCOUNT_OFFER"
        urgency = "WITHIN_7_DAYS"
        confidence = "MODERATE"
        reason = "Medium churn risk with meaningful revenue exposure"
    else:
        action = "NO_ACTION"
        urgency = "LOW"
        confidence = "LOW"
        reason = "Low churn risk"

    expected_loss = round(prob * request.revenue, 2)
    priority_score = round(prob * expected_loss, 2)

    insert_prediction(
        customer_id=request.customer_id,
        churn_probability=round(prob, 4),
        risk_bucket=risk,
        revenue=request.revenue,
        expected_revenue_loss=expected_loss,
        priority_score=priority_score,
        model_version="v1.0"
    )

    return {
        "customer_id": request.customer_id,

        "prediction": {
            "churn_probability": round(prob, 4),
            "risk_bucket": risk,
            "confidence": confidence
        },

        "financial_impact": {
            "customer_revenue": request.revenue,
            "expected_revenue_loss": expected_loss,
            "priority_score": priority_score
        },

        "recommended_action": {
            "action": action,
            "urgency": urgency,
            "reason": reason
        },

        "model_info": {
            "model_version": "v1.0",
            "prediction_time": datetime.utcnow().isoformat() + "Z"
        }
    }

# ===============================
# Dashboard APIs (Frontend-Ready)
# ===============================
@app.get("/api/dashboard/summary")
def dashboard_summary():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            COUNT(*) AS total_predictions,
            ROUND(AVG(churn_probability), 4) AS avg_churn_probability,
            SUM(CASE WHEN risk_bucket='HIGH' THEN 1 ELSE 0 END) AS high_risk_customers,
            ROUND(SUM(expected_revenue_loss), 2) AS total_revenue_at_risk
        FROM customers_predictions
    """)

    data = cursor.fetchone()
    cursor.close()
    conn.close()
    return data

@app.get("/api/dashboard/priority_customers")
def priority_customers():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            customer_id,
            churn_probability,
            risk_bucket,
            expected_revenue_loss,
            priority_score,
            prediction_timestamp
        FROM customers_predictions
        ORDER BY priority_score DESC
        LIMIT 20
    """)

    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

# ===============================
# Root
# ===============================
@app.get("/")
def root():
    return {
        "service": "churn-intelligence-api",
        "status": "running"
    }
