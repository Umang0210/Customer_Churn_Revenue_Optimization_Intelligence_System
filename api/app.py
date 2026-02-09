from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
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
# Paths (Docker-safe)
# ===============================
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models"

# ===============================
# Load ML Assets (Fail Fast)
# ===============================
try:
    model = joblib.load(MODEL_DIR / "churn_model.pkl")
except Exception as e:
    raise RuntimeError(f"❌ Failed to load model: {e}")

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
# Database Connection
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
        raise HTTPException(status_code=500, detail=f"DB connection failed: {e}")

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
# Predict
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
        "churn_probability": round(prob, 4),
        "risk_bucket": risk,
        "expected_revenue_loss": expected_loss,
        "priority_score": priority_score
    }

# ===============================
# Read APIs
# ===============================
@app.get("/api/customers")
def get_customers():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM customers_predictions ORDER BY priority_score DESC LIMIT 100")
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data

@app.get("/api/kpis")
def get_kpis():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            COUNT(*) AS total_customers,
            SUM(CASE WHEN risk_bucket='HIGH' THEN 1 ELSE 0 END) AS high_risk_customers,
            ROUND(SUM(CASE WHEN risk_bucket='HIGH' THEN expected_revenue_loss ELSE 0 END), 2)
            AS revenue_at_risk
        FROM customers_predictions
    """)
    data = cursor.fetchone()
    cursor.close()
    conn.close()
    return data

@app.get("/api/risk_distribution")
def risk_distribution():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT risk_bucket, COUNT(*) AS count
        FROM customers_predictions
        GROUP BY risk_bucket
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
