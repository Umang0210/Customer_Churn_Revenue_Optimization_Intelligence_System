@app.get("/api/risk_distribution")
def risk_distribution():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            risk_bucket,
            COUNT(*) AS count
        FROM customer_churn_analytics
        GROUP BY risk_bucket
        ORDER BY FIELD(risk_bucket, 'HIGH', 'MEDIUM', 'LOW')
    """)

    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data
