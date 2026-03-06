/**
 * Fraud Detection Dashboard - Charts Module
 * Chart.js visualizations for real-time fraud monitoring
 */

// Global chart instances
let fraudChart = null;
let volumeChart = null;

// Chart color palette
const chartColors = {
    normal: '#2ed573',
    fraud: '#ff4757',
    primary: '#00d9ff',
    secondary: '#00ff88',
    grid: 'rgba(255, 255, 255, 0.05)',
    text: '#8b9dc3'
};

// Initialize all charts
function initCharts() {
    initFraudPieChart();
    initVolumeLineChart();
}

/**
 * Initialize Fraud vs Normal Pie/Doughnut Chart
 */
function initFraudPieChart() {
    const ctx = document.getElementById('fraudChart');
    if (!ctx) return;
    
    fraudChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Normal', 'Fraud'],
            datasets: [{
                data: [0, 0],
                backgroundColor: [
                    chartColors.normal,
                    chartColors.fraud
                ],
                borderColor: [
                    'rgba(46, 213, 115, 0.5)',
                    'rgba(255, 71, 87, 0.5)'
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
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(10, 14, 23, 0.9)',
                    titleColor: '#ffffff',
                    bodyColor: '#8b9dc3',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? ((context.raw / total) * 100).toFixed(1) : 0;
                            return `${context.label}: ${context.raw} (${percentage}%)`;
                        }
                    }
                }
            },
            animation: {
                animateRotate: true,
                animateScale: true,
                duration: 800,
                easing: 'easeOutQuart'
            }
        }
    });
}

/**
 * Initialize Transaction Volume Line Chart
 */
function initVolumeLineChart() {
    const ctx = document.getElementById('volumeChart');
    if (!ctx) return;
    
    // Generate initial labels (last 20 time points)
    const labels = generateTimeLabels(20);
    
    volumeChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Total',
                    data: new Array(20).fill(0),
                    borderColor: chartColors.primary,
                    backgroundColor: 'rgba(0, 217, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: chartColors.primary
                },
                {
                    label: 'Fraud',
                    data: new Array(20).fill(0),
                    borderColor: chartColors.fraud,
                    backgroundColor: 'rgba(255, 71, 87, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 6,
                    pointHoverBackgroundColor: chartColors.fraud
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    align: 'end',
                    labels: {
                        color: chartColors.text,
                        usePointStyle: true,
                        pointStyle: 'circle',
                        padding: 20,
                        font: {
                            size: 11
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(10, 14, 23, 0.9)',
                    titleColor: '#ffffff',
                    bodyColor: '#8b9dc3',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    padding: 12,
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                x: {
                    grid: {
                        color: chartColors.grid,
                        drawBorder: false
                    },
                    ticks: {
                        color: chartColors.text,
                        font: {
                            size: 10
                        },
                        maxTicksLimit: 8
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: chartColors.grid,
                        drawBorder: false
                    },
                    ticks: {
                        color: chartColors.text,
                        font: {
                            size: 10
                        },
                        precision: 0
                    }
                }
            },
            animation: {
                duration: 800,
                easing: 'easeOutQuart'
            }
        }
    });
}

/**
 * Generate time labels for the volume chart
 * @param {number} count - Number of labels to generate
 * @returns {Array} Array of time labels
 */
function generateTimeLabels(count) {
    const labels = [];
    const now = new Date();
    
    for (let i = count - 1; i >= 0; i--) {
        const time = new Date(now.getTime() - i * 3000); // 3 second intervals
        labels.push(formatTimeShort(time));
    }
    
    return labels;
}

/**
 * Format time for chart labels
 */
function formatTimeShort(date) {
    return date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
}

/**
 * Update fraud pie chart with new data
 * @param {number} normalCount - Number of normal transactions
 * @param {number} fraudCount - Number of fraud transactions
 */
function updateFraudChart(normalCount, fraudCount) {
    if (!fraudChart) return;
    
    fraudChart.data.datasets[0].data = [normalCount, fraudCount];
    fraudChart.update('none'); // Update without animation for smoother real-time updates
}

/**
 * Update volume line chart with new data point
 * @param {number} total - Total transactions in this period
 * @param {number} fraud - Fraud transactions in this period
 */
function updateVolumeChart(total, fraud) {
    if (!volumeChart) return;
    
    const data = volumeChart.data;
    
    // Add new data point
    data.labels.push(formatTimeShort(new Date()));
    data.datasets[0].data.push(total);
    data.datasets[1].data.push(fraud);
    
    // Remove oldest data point (keep 20 points)
    if (data.labels.length > 20) {
        data.labels.shift();
        data.datasets[0].data.shift();
        data.datasets[1].data.shift();
    }
    
    volumeChart.update('none');
}

/**
 * Update charts with transaction data
 * @param {Array} transactions - Array of transaction objects
 */
function updateChartsWithTransactions(transactions) {
    if (!transactions || transactions.length === 0) return;
    
    const total = transactions.length;
    const fraud = transactions.filter(t => t.is_fraud).length;
    const normal = total - fraud;
    
    // Update pie chart
    updateFraudChart(normal, fraud);
    
    // Update line chart
    updateVolumeChart(total, fraud);
}

/**
 * Handle time range filter buttons
 */
function setupTimeFilterButtons() {
    const buttons = document.querySelectorAll('.time-btn');
    
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            // Update active state
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Here you would typically fetch data for the selected time range
            // For now, we'll just update the chart display
            const range = btn.dataset.range;
            console.log('Time range selected:', range);
        });
    });
}

/**
 * Animate chart updates (pulse effect when data changes significantly)
 */
function animateChartUpdate(chart) {
    if (!chart) return;
    
    // Add a subtle animation effect
    chart.update({
        duration: 300,
        easing: 'easeOutQuart'
    });
}

// Export functions for use in app.js
window.DashboardCharts = {
    initCharts,
    updateFraudChart,
    updateVolumeChart,
    updateChartsWithTransactions,
    setupTimeFilterButtons,
    animateChartUpdate
};

