document.addEventListener('DOMContentLoaded', () => {
    fetchKPIs();
    fetchSegments();
    fetchRiskDistribution();
    fetchHighRiskCustomers();
    fetchModelMetrics();
});

// Utilities
const formatCurrency = (value) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);

// Determine API Base URL
// If running on file://, assume backend is at localhost:8000
// If running on http://localhost:8000, use relative path
const API_BASE = window.location.protocol === 'file:'
    ? 'http://127.0.0.1:8000'
    : '';

// Global Error Handler
const handleFetchError = (error) => {
    console.error('Fetch error:', error);
    const banner = document.getElementById('error-banner');
    if (banner) {
        banner.style.display = 'flex';
        banner.innerHTML = `⚠️ <strong>Connection Failed:</strong> Could not reach the server at <code>${API_BASE}</code>. Make sure <code>python -m uvicorn ...</code> is running.`;
    }
};

// 1. Fetch KPIs
const fetchKPIs = async () => {
    try {
        const response = await fetch(`${API_BASE}/api/kpis`);
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();

        // Update DOM
        document.getElementById('total-revenue').innerText = formatCurrency(data.total_revenue);
        document.getElementById('revenue-at-risk').innerText = formatCurrency(data.revenue_at_risk);
        document.getElementById('churn-rate').innerText = data.churn_rate_pct + '%';
        document.getElementById('high-risk-pct').innerText = data.high_risk_pct + '%';

        // Update Gauge Chart
        initGaugeChart(data.churn_rate_pct);
    } catch (error) {
        console.error('Error fetching KPIs:', error);
    }
};

// 2. Risk Distribution Chart (Pie)
const fetchRiskDistribution = async () => {
    try {
        const response = await fetch('/api/risk_distribution');
        const data = await response.json(); // [{risk_bucket: "HIGH", count: 120}, ...]

        const labels = data.map(d => d.risk_bucket);
        const values = data.map(d => d.count);
        const colors = labels.map(l => {
            if (l === 'HIGH') return '#ef4444';
            if (l === 'MEDIUM') return '#f59e0b';
            return '#10b981';
        });

        const ctx = document.getElementById('riskDistChart').getContext('2d');
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#94a3b8', usePointStyle: true }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error fetching risk distribution:', error);
    }
};

// 3. Contract Segments Chart (Bar)
const fetchSegments = async () => {
    try {
        const response = await fetch('/api/segments');
        const data = await response.json();

        const labels = data.map(d => d.segment_value); // Month-to-month, etc.
        const churnRates = data.map(d => (d.churn_rate * 100).toFixed(1));

        const ctx = document.getElementById('segmentChart').getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Churn Rate %',
                    data: churnRates,
                    backgroundColor: '#3b82f6',
                    borderRadius: 4,
                    barPercentage: 0.6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: 'rgba(148, 163, 184, 0.1)' },
                        ticks: { color: '#94a3b8' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#94a3b8' }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error fetching segments:', error);
    }
};

// 4. Gauge Chart for Overall Churn
const initGaugeChart = (churnRate) => {
    const ctx = document.getElementById('gaugeChart').getContext('2d');
    const safeRate = 100 - churnRate;

    // Update Text
    document.getElementById('gauge-val').innerText = churnRate + '%';

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Churn', 'Safe'],
            datasets: [{
                data: [churnRate, safeRate],
                backgroundColor: ['#ef4444', 'rgba(255, 255, 255, 0.1)'],
                borderWidth: 0,
                circumference: 180,
                rotation: 270,
                cutout: '80%'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            }
        }
    });
};

// 5. High Risk Customers Table
const fetchHighRiskCustomers = async () => {
    try {
        const response = await fetch('/api/customers');
        const data = await response.json();

        const tbody = document.getElementById('customer-table-body');
        tbody.innerHTML = '';

        data.forEach(customer => {
            const row = document.createElement('tr');

            let badgeClass = 'badge-low';
            if (customer.risk_bucket === 'HIGH') badgeClass = 'badge-high';
            else if (customer.risk_bucket === 'MEDIUM') badgeClass = 'badge-medium';

            row.innerHTML = `
                <td>${customer.customer_id}</td>
                <td><span class="badge ${badgeClass}">${customer.risk_bucket}</span></td>
                <td>${(customer.churn_probability * 100).toFixed(1)}%</td>
                <td class="metric-danger">${formatCurrency(customer.expected_revenue_loss)}</td>
                <td>${formatCurrency(customer.revenue)}</td>
                <td><button class="btn-primary" style="padding:0.25rem 0.5rem; font-size: 0.75rem;">View</button></td>
            `;
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error('Error fetching customers:', error);
    }
};
