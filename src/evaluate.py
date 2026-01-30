import pandas as pd
import joblib
import json
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

DATA_PATH = "data/processed/customer_features.csv"
MODEL_PATH = "models/churn_model.pkl"
SCALER_PATH = "models/scaler.pkl"
TARGET_COL = "churn"


def evaluate_model():
    df = pd.read_csv(DATA_PATH)

    X = df.drop(columns=[TARGET_COL])
    y = df[TARGET_COL]

    X = pd.get_dummies(X, drop_first=True)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler = joblib.load(SCALER_PATH)
    model = joblib.load(MODEL_PATH)

    X_test_scaled = scaler.transform(X_test)

    y_pred = model.predict(X_test_scaled)

    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))


if __name__ == "__main__":
    evaluate_model()
