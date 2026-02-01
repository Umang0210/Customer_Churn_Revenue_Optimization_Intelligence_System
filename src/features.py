import os
import pandas as pd

PROCESSED_DIR = "data/processed"
INPUT_PATH = os.path.join(PROCESSED_DIR, "clean_customers.csv")
OUTPUT_PATH = os.path.join(PROCESSED_DIR, "customer_features.csv")


def create_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # ---------- TENURE-BASED FEATURES ----------
    if "tenure" in df.columns:
        df["tenure_group"] = pd.cut(
            df["tenure"],
            bins=[-1, 6, 12, 24, 48, 100],
            labels=["0-6", "6-12", "12-24", "24-48", "48+"]
        )

    # ---------- SPENDING BEHAVIOR ----------
    if {"totalcharges", "tenure"}.issubset(df.columns):
        df["avg_monthly_spend"] = df["totalcharges"] / (df["tenure"] + 1)

    # ---------- COMPLAINT SIGNAL ----------
    if "complaints_count" in df.columns:
        df["has_complaints"] = (df["complaints_count"] > 0).astype(int)

    # ---------- PAYMENT RISK ----------
    if "payment_delays" in df.columns:
        df["delayed_payments_flag"] = (df["payment_delays"] > 0).astype(int)

    return df


def run_feature_engineering():
    if not os.path.exists(INPUT_PATH):
        raise FileNotFoundError("Cleaned data not found. Run cleaning.py first.")

    df = pd.read_csv(INPUT_PATH)

    feature_df = create_features(df)

    feature_df.to_csv(OUTPUT_PATH, index=False)

    print(f"Feature dataset saved to: {OUTPUT_PATH}")
    print(f"Final shape: {feature_df.shape}")


if __name__ == "__main__":
    run_feature_engineering()
    