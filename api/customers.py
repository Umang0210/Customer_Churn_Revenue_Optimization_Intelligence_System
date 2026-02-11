@app.get("/api/customers")
def get_customers():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            customer_id,
            churn_probability,
            risk_bucket,
            revenue,
            expected_revenue_loss,
            priority_score,
            model_version,
            batch_run_date
        FROM customer_churn_analytics
        ORDER BY priority_score DESC
        LIMIT 100
    """)

    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data
