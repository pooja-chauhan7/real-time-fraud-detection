/**
 * Charts Module for Fraud Detection Dashboard
 * Uses Chart.js for rendering analytics charts
 */

// Chart instances storage
let chartInstances = {};

// Chart color palette
const chartColors = {
    primary: '#4f46e5',
    success: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
    info: '#3b82f6',
    gray: '#6b7280'
};

// Initialize charts when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Chart.js will be loaded dynamically in the analytics tab
    loadChartJS();
});

function loadChartJS() {
    // Check if Chart.js is already loaded
    if (typeof Chart === 'undefined') {
        // Load Chart.js from CDN
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';
        script.onload = () => {
            console.log('Chart.js loaded successfully');
            initializeDefaultCharts();
        };
        script.onerror = () => {
            console.error('Failed to load Chart.js');
            // Fallback to CSS-based charts
            initializeFallbackCharts();
        };
        document.head.appendChild(script);
    } else {
        initializeDefaultCharts();
    }
}

function initializeDefaultCharts() {
    // Create empty chart canvases with default data
    createTransactionTypeChart();
    createDailyTrendChart();
    createRiskDistributionChart();
    createFraudAlertsChart();
}

function initializeFallbackCharts() {
    console.log('Using fallback CSS-based charts');
}

/**
 * Create/Update Transaction Type Distribution Chart
 */
function createTransactionTypeChart(data = null) {
    const ctx = document.getElementById('type-chart');
    if (!ctx) return;

    const chartData = data || {
        'TRANSFER': 35,
        'UPI': 28,
        'CARD': 22,
        'INTERNATIONAL': 10,
        'CASH': 5
    };

    const labels = Object.keys(chartData);
    const values = Object.values(chartData);
    const colors = [
        chartColors.primary,
        chartColors.success,
        chartColors.warning,
        chartColors.danger,
        chartColors.info
    ];

    if (chartInstances.typeChart) {
        chartInstances.typeChart.destroy();
    }

    chartInstances.typeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors,
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        usePointStyle: true
                    }
                }
            },
            cutout: '60%'
        }
    });
}

/**
 * Create/Update Daily Transaction Trend Chart
 */
function createDailyTrendChart(data = null) {
    const ctx = document.getElementById('daily-chart');
    if (!ctx) return;

    // Default data for last 7 days
    const defaultData = {
        labels: generateLast7Days(),
        total: [45, 52, 38, 65, 48, 72, 55],
        fraud: [3, 5, 2, 8, 4, 12, 6]
    };

    const chartData = data || defaultData;

    if (chartInstances.dailyChart) {
        chartInstances.dailyChart.destroy();
    }

    chartInstances.dailyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: chartData.labels,
            datasets: [
                {
                    label: 'Total Transactions',
                    data: chartData.total,
                    borderColor: chartColors.primary,
                    backgroundColor: 'rgba(79, 70, 229, 0.1)',
                    fill: true,
                    tension: 0.4
                },
                {
                    label: 'Fraudulent',
                    data: chartData.fraud,
                    borderColor: chartColors.danger,
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    fill: true,
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        usePointStyle: true
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

/**
 * Create/Update Risk Distribution Chart
 */
function createRiskDistributionChart(data = null) {
    const containerId = 'risk-chart';
    let container = document.getElementById(containerId);

    if (!container) {
        // Create container if it doesn't exist
        const riskSummary = document.querySelector('.risk-summary');
        if (riskSummary) {
            const chartContainer = document.createElement('div');
            chartContainer.id = containerId;
            chartContainer.style.cssText = 'width: 100%; height: 200px; margin-top: 20px;';
            riskSummary.appendChild(chartContainer);
            container = chartContainer;
        }
    }

    if (!container) return;

    const chartData = data || {
        LOW: 65,
        MEDIUM: 25,
        HIGH: 10
    };

    const labels = Object.keys(chartData);
    const values = Object.values(chartData);
    const colors = [
        chartColors.success,
        chartColors.warning,
        chartColors.danger
    ];

    if (chartInstances.riskChart) {
        chartInstances.riskChart.destroy();
    }

    chartInstances.riskChart = new Chart(container, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Risk Distribution',
                data: values,
                backgroundColor: colors,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });
}

/**
 * Create/Update Fraud Alerts Chart
 */
function createFraudAlertsChart() {
    const containerId = 'alerts-chart';
    let container = document.getElementById(containerId);

    if (!container) {
        const alertsPanel = document.querySelector('.alerts-panel .panel-content');
        if (alertsPanel) {
            const chartContainer = document.createElement('div');
            chartContainer.id = containerId;
            chartContainer.style.cssText = 'width: 100%; height: 200px;';
            chartContainer.style.marginBottom = '20px';
            alertsPanel.insertBefore(chartContainer, alertsPanel.firstChild);
            container = chartContainer;
        }
    }

    if (!container) return;

    // Default data
    const labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    const data = [3, 5, 2, 8, 4, 6, 3];

    if (chartInstances.alertsChart) {
        chartInstances.alertsChart.destroy();
    }

    chartInstances.alertsChart = new Chart(container, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Fraud Alerts',
                data: data,
                backgroundColor: chartColors.danger,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        stepSize: 1
                    }
                }
            }
        }
    });
}

/**
 * Update all charts with fresh data from API
 */
async function updateChartsWithData() {
    try {
        const response = await fetch(`${window.API_BASE_URL || 'http://localhost:5000'}/api/analytics`);
        const data = await response.json();

        if (data.success && data.analytics) {
            const analytics = data.analytics;

            // Update transaction type chart
            if (analytics.by_type && analytics.by_type.length > 0) {
                const typeData = {};
                analytics.by_type.forEach(item => {
                    typeData[item.type] = item.count;
                });
                createTransactionTypeChart(typeData);
            }

            // Update daily trend chart
            if (analytics.daily && analytics.daily.length > 0) {
                const dailyData = {
                    labels: analytics.daily.map(d => d.date),
                    total: analytics.daily.map(d => d.total_transactions),
                    fraud: analytics.daily.map(d => d.fraud_transactions)
                };
                createDailyTrendChart(dailyData);
            }
        }

        // Also update stats
        const statsResponse = await fetch(`${window.API_BASE_URL || 'http://localhost:5000'}/api/stats`);
        const statsData = await statsResponse.json();

        if (statsData.success && statsData.stats.risk_distribution) {
            createRiskDistributionChart(statsData.stats.risk_distribution);
        }

    } catch (error) {
        console.error('Error updating charts:', error);
    }
}

/**
 * Generate last 7 days labels
 */
function generateLast7Days() {
    const days = [];
    for (let i = 6; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        days.push(date.toLocaleDateString('en-US', { weekday: 'short' }));
    }
    return days;
}

/**
 * Format number with locale
 */
function formatNumber(num) {
    return new Intl.NumberFormat('en-US').format(num);
}

/**
 * Export chart as image
 */
function exportChart(chartId) {
    const chart = chartInstances[chartId];
    if (chart) {
        const link = document.createElement('a');
        link.download = `chart-${chartId}-${Date.now()}.png`;
        link.href = chart.toBase64Image();
        link.click();
    }
}

