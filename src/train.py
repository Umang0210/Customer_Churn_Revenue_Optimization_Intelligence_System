import os
import sys
import json
import pandas as pd
import joblib

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

DATA_PATH = "data/processed/customer_features.csv"
MODEL_DIR = "models"
TARGET_COL = "churn"

MIN_AUC = 0.75  # CI QUALITY GATE


def train_model():
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError("Feature dataset not found. Run features.py first.")

    df = pd.read_csv(DATA_PATH)

    if TARGET_COL not in df.columns:
        raise ValueError("Target column not found in dataset.")

    X = df.drop(columns=[TARGET_COL])
    y = df[TARGET_COL]

    # One-hot encode categoricals
    X = pd.get_dummies(X, drop_first=True)

    feature_names = X.columns.tolist()

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = LogisticRegression(max_iter=1000)
    model.fit(X_train_scaled, y_train)

    y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]
    auc = roc_auc_score(y_test, y_pred_proba)

    print(f"ROC-AUC: {auc:.4f}")

    # ---------------- CI QUALITY GATE ----------------
    if auc < MIN_AUC:
        print(f"❌ Model failed quality gate (AUC < {MIN_AUC})")
        sys.exit(1)

    print("✅ Model passed quality gate")

    # ---------------- SAVE ARTIFACTS ----------------
    os.makedirs(MODEL_DIR, exist_ok=True)

    joblib.dump(model, f"{MODEL_DIR}/churn_model.pkl")
    joblib.dump(scaler, f"{MODEL_DIR}/scaler.pkl")

    with open(f"{MODEL_DIR}/feature_list.json", "w") as f:
        json.dump(feature_names, f)

    print("Model artifacts saved successfully")


if __name__ == "__main__":
    train_model()
    