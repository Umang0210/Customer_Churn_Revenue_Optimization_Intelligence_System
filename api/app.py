import os
import logging
from datetime import date
from pathlib import Path

import joblib
import json
import pandas as pd
import mysql.connector
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# ===============================
# Load Environment Variables
# ===============================
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "churn_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "StrongPassword123")
DB_NAME = os.getenv("DB_NAME", "churn_intelligence")
MODEL_VERSION = os.getenv("MODEL_VERSION", "v1.1.0")

# Detect CI Mode
CI_MODE = os.getenv("CI_MODE", "false").lower() == "true"

# ===============================
# Risk Thresholds
# ===============================
HIGH_THRESHOLD = 0.6
MEDIUM_THRESHOLD = 0.4

# ===============================
# Logging
# ===============================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("churn-api")

# ===============================
# App Init
# ===============================
app = FastAPI(
    title="Churn Intelligence API",
    version="3.1.0"
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
    logger.info("Model loaded successfully.")
except Exception as e:
    logger.error(f"Model loading failed: {e}")
    raise RuntimeError("Model could not be loaded.")

if (MODEL_DIR / "scaler.pkl").exists():
    scaler = joblib.load(MODEL_DIR / "scaler.pkl")
    logger.info("Scaler loaded.")
else:
    scaler = None
    logger.info("No scaler found. Tree-based model assumed.")

try:
    with open(MODEL_DIR / "feature_list.json") as f:
        feature_list = json.load(f)
except:
    feature_list = []

# ===============================
# Database
# ===============================
def get_db_connection():
    if CI_MODE:
        return None

    try:
        return mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None


def insert_prediction(record: dict):
    if CI_MODE:
        return  # Skip DB writes in CI

    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()

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

        cursor.execute(query, (
            record["customer_id"],
            record["churn_probability"],
            record["risk_bucket"],
            record["revenue"],
            record["expected_revenue_loss"],
            record["priority_score"],
            MODEL_VERSION,
            date.today()
        ))

        conn.commit()
        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"Insert failed: {e}")

# ===============================
# Request Schema
# ===============================
class ChurnRequest(BaseModel):
    customer_id: str
    revenue: float = Field(gt=0)

    # Must match training features
    tenure: float = Field(ge=0)
    monthlycharges: float = Field(gt=0)
    totalcharges: float = Field(ge=0)

    gender: str
    seniorcitizen: str
    contract: str

# ===============================
# Health
# ===============================
@app.get("/health")
def health():
    return {"status": "ok"}

# ===============================
# Model Info
# ===============================
@app.get("/model-info")
def model_info():
    try:
        with open(MODEL_DIR / "model_metadata.json") as f:
            return json.load(f)
    except:
        return {"message": "Model metadata not available"}

# ===============================
# Predict
# ===============================
@app.post("/predict")
def predict(request: ChurnRequest):

    try:
        df = pd.DataFrame([request.dict()])
        df.columns = df.columns.str.lower()

        categorical_cols = ["gender", "seniorcitizen", "contract"]
        df_encoded = pd.get_dummies(df, columns=categorical_cols, drop_first=True)

        df_final = df_encoded.reindex(columns=feature_list, fill_value=0)

        if scaler:
            X = scaler.transform(df_final)
        else:
            X = df_final

        prob = float(model.predict_proba(X)[0][1])

    except Exception as e:
        logger.error(f"Inference failed: {e}")
        raise HTTPException(status_code=500, detail="Model inference failed")

    if prob >= HIGH_THRESHOLD:
        risk = "HIGH"
    elif prob >= MEDIUM_THRESHOLD:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    expected_loss = round(prob * request.revenue, 2)
    priority_score = expected_loss

    result = {
        "customer_id": request.customer_id,
        "churn_probability": round(prob, 4),
        "risk_bucket": risk,
        "revenue": request.revenue,
        "expected_revenue_loss": expected_loss,
        "priority_score": priority_score
    }

    insert_prediction(result)

    return result

# ===============================
# Dashboard APIs
# ===============================
@app.get("/api/dashboard/summary")
def dashboard_summary():
    conn = get_db_connection()
    if conn is None:
        return {
            "total_predictions": 0,
            "avg_churn_probability": 0,
            "high_risk_customers": 0,
            "total_revenue_at_risk": 0
        }

    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            COUNT(*) AS total_predictions,
            ROUND(AVG(churn_probability) * 100, 2) AS avg_churn_probability,
            SUM(CASE WHEN risk_bucket='HIGH' THEN 1 ELSE 0 END) AS high_risk_customers,
            IFNULL(ROUND(SUM(expected_revenue_loss), 2), 0) AS total_revenue_at_risk
        FROM customer_churn_analytics
    """)
    data = cursor.fetchone()
    cursor.close()
    conn.close()
    return data


@app.get("/api/dashboard/priority_customers")
def priority_customers():
    conn = get_db_connection()
    if conn is None:
        return []

    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT customer_id,
               churn_probability,
               risk_bucket,
               expected_revenue_loss,
               priority_score
        FROM customer_churn_analytics
        ORDER BY priority_score DESC
        LIMIT 20
    """)
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data


@app.get("/api/risk_distribution")
def risk_distribution():
    conn = get_db_connection()
    if conn is None:
        return []

    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT risk_bucket, COUNT(*) AS count
        FROM customer_churn_analytics
        GROUP BY risk_bucket
    """)
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data


@app.get("/")
def root():
    return {
        "service": "churn-intelligence-api",
        "version": MODEL_VERSION,
        "status": "running"
    }
