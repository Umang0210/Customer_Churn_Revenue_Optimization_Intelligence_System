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

# ===============================
# Risk Thresholds (Aligned with Evaluation)
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

# Load scaler only if exists
if (MODEL_DIR / "scaler.pkl").exists():
    scaler = joblib.load(MODEL_DIR / "scaler.pkl")
    logger.info("Scaler loaded.")
else:
    scaler = None
    logger.info("No scaler found. Tree-based model assumed.")

# Load feature list
try:
    with open(MODEL_DIR / "feature_list.json") as f:
        feature_list = json.load(f)
except:
    feature_list = []

# ===============================
# Database Connection
# ===============================
def get_db_connection():
    try:
        return mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

def insert_prediction(record: dict):
    try:
        conn = get_db_connection()
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
        raise HTTPException(status_code=500, detail="Failed to store prediction")

# ===============================
# Request Schema
# ===============================
class ChurnRequest(BaseModel):
    customer_id: str
    revenue: float = Field(gt=0)
    monthly_charges: float = Field(gt=0)
    usage_frequency: int = Field(ge=0)
    complaints_count: int = Field(ge=0)
    payment_delays: int = Field(ge=0)
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
# Model Info Endpoint
# ===============================
@app.get("/model-info")
def model_info():
    try:
        with open(MODEL_DIR / "model_metadata.json") as f:
            return json.load(f)
    except:
        return {"message": "Model metadata not available"}

# ===============================
# Prediction Endpoint
# ===============================
@app.post("/predict")
def predict(request: ChurnRequest):

    try:
        df = pd.DataFrame([request.dict()])
        df.columns = df.columns.str.lower()

        categorical_cols = ["gender", "seniorcitizen", "contract"]
        df_encoded = pd.get_dummies(df, columns=categorical_cols, drop_first=True)

        df_final = df_encoded.reindex(columns=feature_list, fill_value=0)

        # Apply scaler only if exists
        if scaler:
            X = scaler.transform(df_final)
        else:
            X = df_final

        prob = float(model.predict_proba(X)[0][1])

    except Exception as e:
        logger.error(f"Inference failed: {e}")
        raise HTTPException(status_code=500, detail="Model inference failed")

    # ===============================
    # Risk Logic (Aligned with Evaluation)
    # ===============================
    if prob >= HIGH_THRESHOLD:
        risk = "HIGH"
    elif prob >= MEDIUM_THRESHOLD:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    expected_loss = round(prob * request.revenue, 2)

    # Priority aligned with business logic
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
