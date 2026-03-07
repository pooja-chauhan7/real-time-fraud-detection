/**
 * Professional Charts Module
 * Real-time fraud detection dashboard charts
 */

// Global chart instances
let fraudPieChart = null;
let transactionLineChart = null;
let volumeBarChart = null;

// Initialize all charts
function initDashboardCharts() {
    initFraudPieChart();
    initTransactionLineChart();
    initVolumeBarChart();
}

// Fraud vs Normal Transactions Pie Chart
function initFraudPieChart() {
    const ctx = document.getElementById('fraud-pie-chart');
    if (!ctx) return;
    
    fraudPieChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Normal Transactions', 'Fraud Detected'],
            datasets: [{
                data: [85, 15],
                backgroundColor: [
                    'rgba(16, 185, 129, 0.8)',  // Success green
                    'rgba(239, 68, 68, 0.8)'    // Danger red
                ],
                borderColor: [
                    'rgba(16, 185, 129, 1)',
                    'rgba(239, 68, 68, 1)'
                ],
                borderWidth: 2,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#94a3b8',
                        padding: 20,
                        font: {
                            size: 12,
                            family: "'Inter', sans-serif"
                        },
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleColor: '#f1f5f9',
                    bodyColor: '#94a3b8',
                    borderColor: 'rgba(148, 163, 184, 0.2)',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.raw / total) * 100).toFixed(1);
                            return ` ${context.label}: ${context.raw} (${percentage}%)`;
                        }
                    }
                }
            },
            animation: {
                animateRotate: true,
                animateScale: true,
                duration: 1000,
                easing: 'easeOutQuart'
            }
        }
    });
}

// Transaction Trend Line Chart
function initTransactionLineChart() {
    const ctx = document.getElementById('transaction-line-chart');
    if (!ctx) return;
    
    // Generate last 12 hours of data
    const hours = [];
    const normalData = [];
    const fraudData = [];
    
    for (let i = 11; i >= 0; i--) {
        const hour = new Date();
        hour.setHours(hour.getHours() - i);
        hours.push(hour.getHours() + ':00');
        normalData.push(Math.floor(Math.random() * 30) + 10);
        fraudData.push(Math.floor(Math.random() * 5) + 1);
    }
    transactionLineChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: hours,
            datasets: [
                {
                    label: 'Normal Transactions',
                    data: normalData,
                    borderColor: 'rgba(16, 185, 129, 1)',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: 'rgba(16, 185, 129, 1)',
                    pointBorderColor: '#1e293b',
                    pointBorderWidth: 2
                },
                {
                    label: 'Fraud Detected',
                    data: fraudData,
                    borderColor: 'rgba(239, 68, 68, 1)',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: 'rgba(239, 68, 68, 1)',
                    pointBorderColor: '#1e293b',
                    pointBorderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#94a3b8',
                        padding: 20,
                        font: {
                            size: 12,
                            family: "'Inter', sans-serif"
                        },
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleColor: '#f1f5f9',
                    bodyColor: '#94a3b8',
                    borderColor: 'rgba(148, 163, 184, 0.2)',
                    borderWidth: 1,
                    padding: 12
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#94a3b8',
                        font: {
                            size: 11
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#94a3b8',
                        font: {
                            size: 11
                        },
                        stepSize: 10
                    }
                }
            },
            animation: {
                duration: 1000,
                easing: 'easeOutQuart'
            }
        }
    });
}

// Transaction Volume Bar Chart
function initVolumeBarChart() {
    const ctx = document.getElementById('volume-bar-chart');
    if (!ctx) return;
    
    // Generate weekly data
    const days = [];
    const amounts = [];
    
    for (let i = 6; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        days.push(date.toLocaleDateString('en-US', { weekday: 'short' }));
        amounts.push(Math.floor(Math.random() * 500000) + 100000);
    }
    
    volumeBarChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: days,
            datasets: [{
                label: 'Transaction Volume (₹)',
                data: amounts,
                backgroundColor: (context) => {
                    const gradient = context.chart.ctx.createLinearGradient(0, 0, 0, 300);
                    gradient.addColorStop(0, 'rgba(59, 130, 246, 0.8)');
                    gradient.addColorStop(1, 'rgba(59, 130, 246, 0.4)');
                    return gradient;
                },
                borderColor: 'rgba(59, 130, 246, 1)',
                borderWidth: 1,
                borderRadius: 8,
                hoverBackgroundColor: 'rgba(59, 130, 246, 1)'
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
                    backgroundColor: 'rgba(15, 23, 42, 0.9)',
                    titleColor: '#f1f5f9',
                    bodyColor: '#94a3b8',
                    borderColor: 'rgba(148, 163, 184, 0.2)',
                    borderWidth: 1,
                    padding: 12,
                    callbacks: {
                        label: function(context) {
                            return ' ₹' + context.raw.toLocaleString();
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#94a3b8',
                        font: {
                            size: 11
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(148, 163, 184, 0.1)',
                        drawBorder: false
                    },
                    ticks: {
                        color: '#94a3b8',
                        font: {
                            size: 11
                        },
                        callback: function(value) {
                            return '₹' + (value / 1000).toFixed(0) + 'K';
                        }
                    }
                }
            },
            animation: {
                duration: 1000,
                easing: 'easeOutQuart'
            }
        }
    });
}

// Update charts with real data
function updateChartsWithData(stats, analytics) {
    // Update pie chart
    if (fraudPieChart) {
        fraudPieChart.data.datasets[0].data = [
            stats.normal_transactions || 0,
            stats.fraud_transactions || 0
        ];
        fraudPieChart.update('none');
    }
    
    // Update line chart with new data
    if (transactionLineChart && analytics && analytics.daily) {
        const labels = analytics.daily.map(d => d.date);
        const normalData = analytics.daily.map(d => d.total_transactions - d.fraud_transactions);
        const fraudData = analytics.daily.map(d => d.fraud_transactions);
        
        transactionLineChart.data.labels = labels;
        transactionLineChart.data.datasets[0].data = normalData;
        transactionLineChart.data.datasets[1].data = fraudData;
        transactionLineChart.update('none');
    }
}

// Add new data point to line chart
function addDataPoint(normalCount, fraudCount) {
    if (!transactionLineChart) return;
    
    const now = new Date();
    const label = now.getHours() + ':00';
    
    // Add new label
    transactionLineChart.data.labels.push(label);
    if (transactionLineChart.data.labels.length > 12) {
        transactionLineChart.data.labels.shift();
    }
    
    // Add new data points
    transactionLineChart.data.datasets[0].data.push(normalCount);
    if (transactionLineChart.data.datasets[0].data.length > 12) {
        transactionLineChart.data.datasets[0].data.shift();
    }
    
    transactionLineChart.data.datasets[1].data.push(fraudCount);
    if (transactionLineChart.data.datasets[1].data.length > 12) {
        transactionLineChart.data.datasets[1].data.shift();
    }
    
    transactionLineChart.update('none');
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboardCharts);
} else {
    initDashboardCharts();
}

// Export functions for global use
window.initDashboardCharts = initDashboardCharts;
window.updateChartsWithData = updateChartsWithData;
window.addDataPoint = addDataPoint;

