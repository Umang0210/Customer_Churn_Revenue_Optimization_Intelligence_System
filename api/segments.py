@app.get("/api/segments")
def segment_insights():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            CASE
                WHEN revenue < 50 THEN 'Low Revenue'
                WHEN revenue BETWEEN 50 AND 100 THEN 'Mid Revenue'
                ELSE 'High Revenue'
            END AS segment,
            COUNT(*) AS customer_count,
            ROUND(AVG(churn_probability), 4) AS avg_churn_probability,
            ROUND(SUM(expected_revenue_loss), 2) AS revenue_at_risk
        FROM customer_churn_analytics
        GROUP BY segment
        ORDER BY revenue_at_risk DESC
    """)

    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return data
    