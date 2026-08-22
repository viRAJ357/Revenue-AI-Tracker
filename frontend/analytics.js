const API_BASE = 'http://localhost:8001/api';

async function fetchAnalyticsData() {
    const token = localStorage.getItem('recoverai_token');
    if (!token) {
        window.location.href = 'login.html';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/analytics-data`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.status === 401) {
            window.location.href = 'login.html';
            return;
        }

        const data = await response.json();
        renderCharts(data.data);
    } catch (error) {
        console.error("Failed to fetch analytics data", error);
    }
}

function renderCharts(data) {
    const dates = data.dates.map(ts => new Date(ts).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }));

    // Shared Chart.js defaults for dark theme
    Chart.defaults.color = '#8f8fa1';
    Chart.defaults.font.family = 'Inter';
    const gridConfig = { color: 'rgba(255, 255, 255, 0.05)', drawBorder: false };

    // Recovery Rate Chart
    const ctxRate = document.getElementById('recoveryRateChart').getContext('2d');
    new Chart(ctxRate, {
        type: 'line',
        data: {
            labels: dates,
            datasets: [{
                label: 'Recovery Success Rate (%)',
                data: data.recovery_success_rate,
                borderColor: '#50d8e9',
                backgroundColor: 'rgba(80, 216, 233, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, max: 100, grid: gridConfig },
                x: { grid: gridConfig }
            }
        }
    });

    // Revenue Impact Chart
    const ctxRev = document.getElementById('revenueChart').getContext('2d');
    new Chart(ctxRev, {
        type: 'bar',
        data: {
            labels: dates,
            datasets: [
                {
                    label: 'Revenue Recovered',
                    data: data.revenue_recovered,
                    backgroundColor: '#bec2ff',
                    borderRadius: 4
                },
                {
                    label: 'Revenue Lost',
                    data: data.revenue_lost,
                    backgroundColor: '#ffb4ab',
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'top', labels: { usePointStyle: true } }
            },
            scales: {
                y: { beginAtZero: true, grid: gridConfig, stacked: true },
                x: { grid: gridConfig, stacked: true }
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', fetchAnalyticsData);
