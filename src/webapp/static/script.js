const BASE_URL = "http://127.0.0.1:8000";

// Chart.js Global Configuration for Dark Theme
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = '#334155';
Chart.defaults.font.family = 'Inter, sans-serif';

// ========================
// FETCH DASHBOARD SUMMARY
// ========================
async function loadSummary() {
    try {
        const res = await fetch(`${BASE_URL}/api/dashboard/summary`);
        const data = await res.json();

        document.getElementById("totalPredictions").innerText = data.total_predictions || 0;
        document.getElementById("avgChurn").innerText = (data.avg_churn_probability || 0).toFixed(2) + '%';
        document.getElementById("highRisk").innerText = data.high_risk_customers || 0;
        document.getElementById("revenueRisk").innerText = "₹" + (data.total_revenue_at_risk || 0).toLocaleString('en-IN');
    } catch (error) {
        console.error("Error loading summary:", error);
        // Set placeholder values on error
        document.getElementById("totalPredictions").innerText = "0";
        document.getElementById("avgChurn").innerText = "0%";
        document.getElementById("highRisk").innerText = "0";
        document.getElementById("revenueRisk").innerText = "₹0";
    }
}

// ========================
// FETCH PRIORITY CUSTOMERS
// ========================
async function loadCustomers() {
    try {
        const res = await fetch(`${BASE_URL}/api/dashboard/priority_customers`);
        const customers = await res.json();

        const tbody = document.getElementById("customerTable");
        tbody.innerHTML = "";

        const riskCounts = { HIGH: 0, MEDIUM: 0, LOW: 0 };
        const names = [];
        const priorityScores = [];

        customers.forEach(c => {
            riskCounts[c.risk_bucket]++;

            names.push(c.customer_id);
            priorityScores.push(c.priority_score);

            const riskBadge = getRiskBadge(c.risk_bucket);
            const row = `
        <tr>
          <td><strong>${c.customer_id}</strong></td>
          <td>${riskBadge}</td>
          <td>${(c.churn_probability * 100).toFixed(1)}%</td>
          <td>₹${c.expected_revenue_loss.toLocaleString('en-IN')}</td>
          <td><strong>${c.priority_score.toFixed(2)}</strong></td>
        </tr>
      `;
            tbody.innerHTML += row;
        });

        drawRiskChart(riskCounts);
        drawPriorityChart(names, priorityScores);
    } catch (error) {
        console.error("Error loading customers:", error);
    }
}

// ========================
// RISK BADGE HELPER
// ========================
function getRiskBadge(risk) {
    const colors = {
        HIGH: '#ef4444',
        MEDIUM: '#f59e0b',
        LOW: '#10b981'
    };
    return `<span style="color: ${colors[risk]}; font-weight: 600;">● ${risk}</span>`;
}

// ========================
// CHARTS
// ========================
function drawRiskChart(riskCounts) {
    const ctx = document.getElementById("riskChart");
    new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: ["HIGH", "MEDIUM", "LOW"],
            datasets: [{
                data: [
                    riskCounts.HIGH,
                    riskCounts.MEDIUM,
                    riskCounts.LOW
                ],
                backgroundColor: [
                    "#ef4444",
                    "#f59e0b",
                    "#10b981"
                ],
                borderWidth: 0,
                hoverOffset: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        font: {
                            size: 13,
                            weight: '500'
                        },
                        color: '#94a3b8'
                    }
                },
                tooltip: {
                    backgroundColor: '#1e293b',
                    titleColor: '#f1f5f9',
                    bodyColor: '#f1f5f9',
                    borderColor: '#334155',
                    borderWidth: 1,
                    padding: 12,
                    bodyFont: {
                        size: 14
                    }
                }
            }
        }
    });
}

function drawPriorityChart(names, scores) {
    const ctx = document.getElementById("priorityChart");
    new Chart(ctx, {
        type: "bar",
        data: {
            labels: names,
            datasets: [{
                label: "Priority Score",
                data: scores,
                backgroundColor: "#8b5cf6",
                borderRadius: 6,
                hoverBackgroundColor: "#a78bfa"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: '#1e293b',
                    titleColor: '#f1f5f9',
                    bodyColor: '#f1f5f9',
                    borderColor: '#334155',
                    borderWidth: 1,
                    padding: 12,
                    bodyFont: {
                        size: 14
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: '#334155',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#94a3b8',
                        font: {
                            size: 12
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#94a3b8',
                        font: {
                            size: 12
                        }
                    }
                }
            }
        }
    });
}

// ========================
// INIT
// ========================
loadSummary();
loadCustomers();
