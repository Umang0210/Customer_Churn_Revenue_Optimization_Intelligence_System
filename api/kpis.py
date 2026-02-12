@app.get("/api/kpis")
def get_kpis():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            COUNT(*) AS total_customers,
            ROUND(AVG(churn_probability), 4) AS avg_churn_probability,
            SUM(CASE WHEN risk_bucket = 'HIGH' THEN 1 ELSE 0 END)
                AS high_risk_customers,
            ROUND(SUM(expected_revenue_loss), 2)
                AS total_revenue_at_risk
        FROM customer_churn_analytics
    """)

    data = cursor.fetchone()
    cursor.close()
    conn.close()
    return data