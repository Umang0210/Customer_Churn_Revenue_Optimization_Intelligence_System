import os
import json
import joblib
import pandas as pd
from datetime import datetime, timezone

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, precision_score, recall_score


# -----------------------------
# CONFIG
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RANDOM_STATE = 42
MODEL_DIR = os.path.join(BASE_DIR, "../models/")
TARGET_COL = "churn"


# -----------------------------
# LOAD DATA
# -----------------------------
def load_data():
    csv_path = os.path.join(BASE_DIR, "../data/processed/customer_features.csv")
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Data file not found at {csv_path}")
    df = pd.read_csv(csv_path)
    return df

# -----------------------------
# EVALUATION
# -----------------------------
def evaluate_model(model, X_test, y_test, threshold=0.5):
    y_prob = model.predict_proba(X_test)[:, 1]
    y_pred = (y_prob >= threshold).astype(int)

    return {
        "roc_auc": round(roc_auc_score(y_test, y_prob), 4),
        "precision": round(precision_score(y_test, y_pred), 4),
        "recall": round(recall_score(y_test, y_pred), 4),
    }


# -----------------------------
# MAIN TRAINING PIPELINE
# -----------------------------
def main():
    # Load data
    df = load_data()

    # -----------------------------
    # SCHEMA NORMALIZATION
    # -----------------------------
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    # -----------------------------
    # DROP ID COLUMN
    # -----------------------------
    df = df.drop(columns=["customerid"])

    # -----------------------------
    # FEATURE GROUPS (REAL COLUMNS)
    # -----------------------------
    NUMERIC_COLS = [
        "tenure",
        "monthlycharges",
        "totalcharges"
    ]

    CATEGORICAL_COLS = [
        "gender",
        "seniorcitizen",
        "contract"
    ]

    # -----------------------------
    # SEPARATE FEATURES & TARGET
    # -----------------------------
    X = df[NUMERIC_COLS + CATEGORICAL_COLS]
    X = df[NUMERIC_COLS + CATEGORICAL_COLS]
    # FIX: Map 'yes'/'no' to 1/0
    y = df[TARGET_COL].map({'yes': 1, 'no': 0})

    # -----------------------------
    # ENCODE CATEGORICAL FEATURES
    # -----------------------------
    X = pd.get_dummies(X, columns=CATEGORICAL_COLS, drop_first=True)

    feature_list = list(X.columns)

    # -----------------------------
    # TRAIN-TEST SPLIT
    # -----------------------------
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=y
    )

    # -----------------------------
    # BASELINE: LOGISTIC REGRESSION
    # -----------------------------
    scaler = StandardScaler()

    X_train_scaled = X_train.copy()
    X_test_scaled = X_test.copy()

    X_train_scaled[NUMERIC_COLS] = scaler.fit_transform(X_train[NUMERIC_COLS])
    X_test_scaled[NUMERIC_COLS] = scaler.transform(X_test[NUMERIC_COLS])

    log_reg = LogisticRegression(
        max_iter=1000,
        class_weight="balanced",
        random_state=RANDOM_STATE
    )

    log_reg.fit(X_train_scaled, y_train)
    log_reg_metrics = evaluate_model(log_reg, X_test_scaled, y_test)

    # -----------------------------
    # CANDIDATE: RANDOM FOREST
    # -----------------------------
    rf = RandomForestClassifier(
        n_estimators=250,
        max_depth=10,
        class_weight="balanced",
        random_state=RANDOM_STATE,
        n_jobs=-1
    )

    rf.fit(X_train, y_train)
    rf_metrics = evaluate_model(rf, X_test, y_test)

    # -----------------------------
    # MODEL COMPARISON & SELECTION
    # -----------------------------
    model_results = {
        "logistic_regression": log_reg_metrics,
        "random_forest": rf_metrics
    }

    if rf_metrics["roc_auc"] >= log_reg_metrics["roc_auc"]:
        selected_model = "random_forest"
        final_model = rf
        final_scaler = None
        final_metrics = rf_metrics
    else:
        selected_model = "logistic_regression"
        final_model = log_reg
        final_scaler = scaler
        final_metrics = log_reg_metrics

    # -----------------------------
    # SAVE ARTIFACTS
    # -----------------------------
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(final_model, f"{MODEL_DIR}churn_model.pkl")

    if final_scaler:
        joblib.dump(final_scaler, f"{MODEL_DIR}scaler.pkl")

    with open(f"{MODEL_DIR}feature_list.json", "w") as f:
        json.dump(feature_list, f, indent=4)

    model_metadata = {
        "model_version": "v1.1.0",
        "training_date": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "selected_model": selected_model,
        "baseline_model": "logistic_regression",
        "metrics": model_results,
        "final_model_metrics": final_metrics,
        "training_rows": int(X_train.shape[0]),
        "test_rows": int(X_test.shape[0]),
        "num_features": len(feature_list),
        "selection_reason": "Selected based on superior ROC-AUC while maintaining recall for churn risk identification"
    }

    with open(f"{MODEL_DIR}model_metadata.json", "w") as f:
        json.dump(model_metadata, f, indent=4)

    print("✅ Training completed successfully")
    print(f"✅ Selected model: {selected_model}")
    print("📊 Final metrics:", final_metrics)


if __name__ == "__main__":
    main()
