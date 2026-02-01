from fastapi import FastAPI
import joblib
import pandas as pd

app = FastAPI(title="Churn Prediction API")

model = joblib.load("models/churn_model.pkl")
scaler = joblib.load("models/scaler.pkl")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict")
def predict(data: dict):
    df = pd.DataFrame([data])
    df = pd.get_dummies(df, drop_first=True)

    df_scaled = scaler.transform(df)

    prob = model.predict_proba(df_scaled)[0][1]

    return {
        "churn_probability": round(float(prob), 4),
        "risk_level": "HIGH" if prob > 0.7 else "MEDIUM" if prob > 0.4 else "LOW"
    }