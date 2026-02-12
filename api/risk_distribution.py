@app.get("/api/risk_distribution")
def risk_distribution():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            risk_bucket,
            COUNT(*) AS count,
            ROUND(AVG(churn_probability), 4) AS avg_probability,
            ROUND(SUM(expected_revenue_loss), 2) AS revenue_at_risk
        FROM customer_churn_analytics
        GROUP BY risk_bucket
        ORDER BY count DESC
    """)

    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data