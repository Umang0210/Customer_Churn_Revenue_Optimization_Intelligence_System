import pandas as pd
import joblib
import json
import sys
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    precision_score,
    recall_score
)
from sklearn.model_selection import train_test_split
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models"
DATA_DIR = BASE_DIR / "data" / "processed"

DATA_PATH = DATA_DIR / "customer_features.csv"
MODEL_PATH = MODEL_DIR / "churn_model.pkl"
SCALER_PATH = MODEL_DIR / "scaler.pkl"
FEATURE_LIST_PATH = MODEL_DIR / "feature_list.json"
TARGET_COL = "churn"


def evaluate_model():

    print("Loading data...")
    df = pd.read_csv(DATA_PATH)

    X = df.drop(columns=[TARGET_COL])
    y = df[TARGET_COL]

    # Encode categoricals
    X = pd.get_dummies(X, drop_first=True)

    # Align features to training schema
    with open(FEATURE_LIST_PATH, "r") as f:
        feature_list = json.load(f)

    X = X.reindex(columns=feature_list, fill_value=0)

    # Train/test split (same random_state as training)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("Loading model & scaler...")
    scaler = joblib.load(SCALER_PATH)
    model = joblib.load(MODEL_PATH)

    X_test_scaled = scaler.transform(X_test)

    print("Running predictions...")
    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)[:, 1]

    # Metrics
    roc_auc = roc_auc_score(y_test, y_proba)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)

    print("\n==============================")
    print("MODEL EVALUATION METRICS")
    print("==============================")
    print(f"ROC-AUC: {roc_auc:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")

    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # 🚨 CI Performance Gate
    MIN_ROC_AUC = 0.70

    if roc_auc < MIN_ROC_AUC:
        print(f"\n❌ Model ROC-AUC below threshold ({MIN_ROC_AUC})")
        sys.exit(1)
    else:
        print("\n✅ Model performance acceptable.")


if __name__ == "__main__":
    evaluate_model()
