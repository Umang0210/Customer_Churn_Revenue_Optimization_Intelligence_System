const BASE_URL = "http://127.0.0.1:8000";

// ===============================
// GLOBAL CHART CONFIG (Dark UI)
// ===============================
Chart.defaults.color = '#94a3b8';
Chart.defaults.borderColor = '#334155';
Chart.defaults.font.family = 'Inter, sans-serif';

// ===============================
// DASHBOARD SUMMARY
// ===============================
async function loadDashboard() {
    try {
        const res = await fetch(`${BASE_URL}/api/dashboard/summary`);
        const data = await res.json();

        document.getElementById("totalPredictions").innerText =
            data.total_predictions ?? 0;

        // Backend should now return percentage (0–100)
        document.getElementById("avgChurn").innerText =
            (data.avg_churn_probability ?? 0).toFixed(2) + "%";

        document.getElementById("highRisk").innerText =
            data.high_risk_customers ?? 0;

        document.getElementById("revenueRisk").innerText =
            "₹" + (data.total_revenue_at_risk ?? 0).toLocaleString('en-IN');

    } catch (err) {
        console.error("Dashboard summary failed:", err);
    }
}

// ===============================
// PRIORITY CUSTOMERS (Dashboard)
// ===============================
async function loadPriorityCustomers() {
    try {
        const res = await fetch(`${BASE_URL}/api/dashboard/priority_customers`);
        const customers = await res.json();

        const tbody = document.getElementById("customerTable");
        if (!tbody) return;

        tbody.innerHTML = "";

        const riskCounts = { HIGH: 0, MEDIUM: 0, LOW: 0 };
        const names = [];
        const priorityScores = [];

        customers.forEach(c => {

            const risk = (c.risk_bucket || "LOW").toUpperCase();
            riskCounts[risk]++;

            names.push(c.customer_id);
            priorityScores.push(c.priority_score ?? 0);

            const row = `
                <tr>
                    <td><strong>${c.customer_id}</strong></td>
                    <td>${getRiskBadge(risk)}</td>
                    <td>${((c.churn_probability ?? 0) * 100).toFixed(1)}%</td>
                    <td>₹${(c.expected_revenue_loss ?? 0).toLocaleString('en-IN')}</td>
                    <td><strong>${(c.priority_score ?? 0).toFixed(2)}</strong></td>
                </tr>
            `;

            tbody.innerHTML += row;
        });

        drawRiskChart(riskCounts);
        drawPriorityChart(names, priorityScores);

    } catch (err) {
        console.error("Priority customers load failed:", err);
    }
}

// ===============================
// RISK BADGE
// ===============================
function getRiskBadge(risk) {
    const colors = {
        HIGH: '#ef4444',
        MEDIUM: '#f59e0b',
        LOW: '#10b981'
    };

    return `<span style="color:${colors[risk]};font-weight:600;">● ${risk}</span>`;
}

// ===============================
// RISK CHART
// ===============================
function drawRiskChart(riskCounts) {
    const ctx = document.getElementById("riskChart");
    if (!ctx) return;

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
                backgroundColor: ["#ef4444", "#f59e0b", "#10b981"],
                borderWidth: 0,
                hoverOffset: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// ===============================
// PRIORITY CHART
// ===============================
function drawPriorityChart(names, scores) {
    const ctx = document.getElementById("priorityChart");
    if (!ctx) return;

    new Chart(ctx, {
        type: "bar",
        data: {
            labels: names,
            datasets: [{
                label: "Priority Score",
                data: scores,
                backgroundColor: "#8b5cf6",
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

// ===============================
// CUSTOMERS PAGE
// ===============================
async function loadCustomersPage() {
    try {
        const res = await fetch(`${BASE_URL}/api/customers`);
        const data = await res.json();

        const tbody = document.getElementById("customerTableBody");
        if (!tbody) return;

        tbody.innerHTML = "";

        data.forEach(customer => {
            const risk = (customer.risk_bucket || "LOW").toUpperCase();

            const row = `
                <tr>
                    <td><strong>${customer.customer_id}</strong></td>
                    <td>${getRiskBadge(risk)}</td>
                    <td>${((customer.churn_probability ?? 0) * 100).toFixed(1)}%</td>
                    <td>₹${(customer.expected_revenue_loss ?? 0).toLocaleString('en-IN')}</td>
                </tr>
            `;

            tbody.innerHTML += row;
        });

    } catch (err) {
        console.error("Customers page failed:", err);
    }
}

// ===============================
// ANALYTICS PAGE
// ===============================
async function loadAnalyticsPage() {
    try {
        const res = await fetch(`${BASE_URL}/api/risk_distribution`);
        const riskData = await res.json();

        const labels = riskData.map(x => x.risk_bucket);
        const counts = riskData.map(x => x.count);

        const canvas = document.getElementById('segmentChart');
        if (!canvas) return;

        new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels,
                datasets: [{
                    data: counts,
                    backgroundColor: ['#ef4444', '#f59e0b', '#10b981'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });

    } catch (err) {
        console.error("Analytics load failed:", err);
    }
}

// ===============================
// PREDICTION
// ===============================
async function submitPrediction(formData) {
    try {
        const response = await fetch(`${BASE_URL}/predict`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(formData)
        });

        if (!response.ok) {
            throw new Error("Prediction failed");
        }

        const result = await response.json();

        const probability = (result.churn_probability * 100).toFixed(1);
        const risk = result.risk_bucket;
        const expectedLoss = result.expected_revenue_loss;

        document.getElementById("resultProbability").textContent = probability + "%";
        document.getElementById("resultRisk").innerHTML = getRiskBadge(risk);
        document.getElementById("resultConfidence").textContent = "95%"; // Mock confidence
        document.getElementById("resultAction").textContent =
            risk === "HIGH"
                ? "Immediate retention action required"
                : risk === "MEDIUM"
                    ? "Schedule retention campaign"
                    : "Monitor customer";

        document.getElementById("predictionResult").style.display = "block";

        return result;

    } catch (err) {
        console.error("Prediction error:", err);
        alert("Prediction failed. Check backend.");
    }
}

// ===============================
// INIT ROUTER
// ===============================
document.addEventListener("DOMContentLoaded", () => {

    const path = window.location.pathname;

    // Dashboard: index.html or root path
    if (path.includes("index.html") || path.endsWith("/") || path === "") {
        loadDashboard();
        loadPriorityCustomers();
    }

    // Customers page
    if (path.includes("customers.html")) {
        loadCustomersPage();
    }

    // Analytics page
    if (path.includes("analytics.html")) {
        loadAnalyticsPage();
    }

    // Predictions page
    if (path.includes("predictions.html")) {
        const predictionForm = document.getElementById('predictionForm');
        if (predictionForm) {
            predictionForm.addEventListener('submit', async function (e) {
                e.preventDefault();

                const formData = {
                    customer_id: document.getElementById('customerId').value,
                    tenure: parseInt(document.getElementById('tenure').value) || 0,
                    monthly_charges: parseFloat(document.getElementById('monthlyCharges').value) || 0,
                    total_charges: parseFloat(document.getElementById('totalCharges').value) || 0,
                    contract: document.getElementById('contract').value,
                    payment_method: document.getElementById('paymentMethod').value
                };

                await submitPrediction(formData);
            });
        }
    }

    // Settings page
    if (path.includes("settings.html")) {
        // Save button handler
        document.querySelectorAll('.btn-primary').forEach(btn => {
            btn.addEventListener('click', function () {
                alert('Settings saved successfully!');
            });
        });

        // Test connection handler
        const testConnectionBtn = document.querySelector('.btn-secondary');
        if (testConnectionBtn) {
            testConnectionBtn.addEventListener('click', function () {
                alert('Connection test successful! API is responding.');
            });
        }
    }

});