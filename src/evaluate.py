import pandas as pd
import joblib
import json
import sys
from pathlib import Path
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    precision_score,
    recall_score
)
from sklearn.model_selection import train_test_split

# ==============================
# CONFIG
# ==============================
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models"
DATA_PATH = BASE_DIR / "data" / "processed" / "customer_features.csv"

MODEL_PATH = MODEL_DIR / "churn_model.pkl"
SCALER_PATH = MODEL_DIR / "scaler.pkl"
FEATURE_LIST_PATH = MODEL_DIR / "feature_list.json"

TARGET_COL = "churn"
RANDOM_STATE = 42


def evaluate_model():

    print("Loading data...")
    df = pd.read_csv(DATA_PATH)

    # Normalize schema
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    # Map target if needed
    if df[TARGET_COL].dtype == object:
        df[TARGET_COL] = df[TARGET_COL].map({'yes': 1, 'no': 0})

    # Explicit feature selection (match training)
    NUMERIC_COLS = ["tenure", "monthlycharges", "totalcharges"]
    CATEGORICAL_COLS = ["gender", "seniorcitizen", "contract"]

    X = df[NUMERIC_COLS + CATEGORICAL_COLS]
    y = df[TARGET_COL]

    # Encode categoricals
    X = pd.get_dummies(X, columns=CATEGORICAL_COLS, drop_first=True)

    # Align features to training schema
    with open(FEATURE_LIST_PATH, "r") as f:
        feature_list = json.load(f)

    X = X.reindex(columns=feature_list, fill_value=0)

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y
    )

    print("Loading model...")
    model = joblib.load(MODEL_PATH)

    # Apply scaler only if it exists
    if SCALER_PATH.exists():
        print("Scaler found. Applying scaling...")
        scaler = joblib.load(SCALER_PATH)
        X_test = scaler.transform(X_test)
    else:
        print("No scaler found. Using raw features.")

    print("Running predictions...")
    y_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= 0.5).astype(int)

    # ==============================
    # METRICS
    # ==============================
    roc_auc = roc_auc_score(y_test, y_proba)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)

    print("\n==============================")
    print("MODEL EVALUATION METRICS")
    print("==============================")
    print(f"ROC-AUC: {roc_auc:.4f}")
    print(f"Precision (0.5 threshold): {precision:.4f}")
    print(f"Recall (0.5 threshold): {recall:.4f}")

    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    # ==============================
    # THRESHOLD ANALYSIS
    # ==============================
    print("\nThreshold Analysis:")
    for t in [0.4, 0.5, 0.6, 0.7]:
        y_pred_t = (y_proba >= t).astype(int)
        print(f"\nThreshold: {t}")
        print("Precision:", round(precision_score(y_test, y_pred_t), 4))
        print("Recall:", round(recall_score(y_test, y_pred_t), 4))

    # ==============================
    # CI PERFORMANCE GATE
    # ==============================
    MIN_ROC_AUC = 0.70

    if roc_auc < MIN_ROC_AUC:
        print(f"\n❌ Model ROC-AUC below threshold ({MIN_ROC_AUC})")
        sys.exit(1)
    else:
        print("\n✅ Model performance acceptable.")

if __name__ == "__main__":
    evaluate_model()