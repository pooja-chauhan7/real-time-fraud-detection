/**
 * Fraud Detection Dashboard - Main Application
 * Real-time transaction monitoring and fraud detection
 */

// ==================== Configuration ====================
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'http://localhost:5000/api' 
    : '/api';

const REFRESH_INTERVAL = 3000; // 3 seconds
const MAX_TRANSACTIONS = 100;
const MAX_ALERTS = 50;

// ==================== State Management ====================
let state = {
    transactions: [],
    alerts: [],
    stats: {
        total_transactions: 0,
        fraud_transactions: 0,
        normal_transactions: 0,
        total_alerts: 0,
        new_alerts: 0,
        fraud_percentage: 0
    },
    isConnected: false,
    lastUpdate: null
};

// ==================== DOM Elements ====================
const elements = {
    // Status
    connectionStatus: document.getElementById('connection-status'),
    statusDot: document.getElementById('status-dot'),
    currentTime: document.getElementById('current-time'),
    
    // Stats
    totalTransactions: document.getElementById('total-transactions'),
    normalTransactions: document.getElementById('normal-transactions'),
    fraudTransactions: document.getElementById('fraud-transactions'),
    activeAlerts: document.getElementById('active-alerts'),
    
    // Trends
    normalTrend: document.getElementById('normal-trend'),
    fraudTrend: document.getElementById('fraud-trend'),
    alertTrend: document.getElementById('alert-trend'),
    txnTrend: document.getElementById('txn-trend'),
    
    // Alerts
    alertBadge: document.getElementById('alert-badge'),
    alertsContainer: document.getElementById('alerts-container'),
    
    // Transactions
    transactionsBody: document.getElementById('transactions-body'),
    
    // Analysis
    avgAmount: document.getElementById('avg-amount'),
    maxAmount: document.getElementById('max-amount'),
    fraudRate: document.getElementById('fraud-rate'),
    txnPerMin: document.getElementById('txn-per-min'),
    
    // Notifications
    notificationContainer: document.getElementById('notification-container')
};

// ==================== Initialization ====================
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing Fraud Detection Dashboard...');
    
    // Initialize charts
    if (typeof DashboardCharts !== 'undefined') {
        DashboardCharts.initCharts();
        DashboardCharts.setupTimeFilterButtons();
    }
    
    // Check API connection
    checkConnection();
    
    // Load initial data
    loadDashboardData();
    
    // Start auto-refresh
    startAutoRefresh();
    
    // Update clock
    updateClock();
    setInterval(updateClock, 1000);
});

// ==================== API Connection ====================
async function checkConnection() {
    try {
        const response = await fetch(`${API_BASE_URL.replace('/api', '')}/`);
        if (response.ok) {
            updateConnectionStatus(true);
        } else {
            updateConnectionStatus(false);
        }
    } catch (error) {
        console.error('Connection error:', error);
        updateConnectionStatus(false);
    }
}

function updateConnectionStatus(connected) {
    state.isConnected = connected;
    
    if (connected) {
        elements.connectionStatus.textContent = 'Connected';
        elements.statusDot.classList.add('connected');
    } else {
        elements.connectionStatus.textContent = 'Disconnected';
        elements.statusDot.classList.remove('connected');
    }
}

// ==================== Data Loading ====================
async function loadDashboardData() {
    try {
        const [statsData, transactionsData, alertsData] = await Promise.all([
            fetchAPI('/stats'),
            fetchAPI('/transactions?limit=50'),
            fetchAPI('/alerts?limit=20')
        ]);
        
        if (statsData.success) {
            state.stats = statsData.stats;
            updateStats(statsData.stats);
        }
        
        if (transactionsData.success) {
            state.transactions = transactionsData.transactions;
            renderTransactions(transactionsData.transactions);
            updateCharts();
        }
        
        if (alertsData.success) {
            state.alerts = alertsData.alerts;
            renderAlerts(alertsData.alerts);
            checkForNewAlerts(alertsData.alerts);
        }
        
        state.lastUpdate = new Date();
        updateConnectionStatus(true);
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        updateConnectionStatus(false);
    }
}

async function fetchAPI(endpoint) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`);
    return await response.json();
}

// ==================== Stats Update ====================
function updateStats(stats) {
    // Update stat cards
    elements.totalTransactions.textContent = formatNumber(stats.total_transactions);
    elements.normalTransactions.textContent = formatNumber(stats.normal_transactions || (stats.total_transactions - stats.fraud_transactions));
    elements.fraudTransactions.textContent = formatNumber(stats.fraud_transactions);
    elements.activeAlerts.textContent = stats.new_alerts || 0;
    
    // Update trends
    const fraudPercent = stats.fraud_percentage || 0;
    elements.fraudTrend.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${fraudPercent}%`;
    
    // Update analysis values
    elements.fraudRate.textContent = `${fraudPercent}%`;
    
    // Calculate transactions per minute (approximate)
    const txnPerMin = Math.round((stats.total_transactions / 60) * 3); // Assuming ~3 min of data
    elements.txnPerMin.textContent = txnPerMin > 0 ? txnPerMin : stats.total_transactions;
    
    // Calculate average and max amount from transactions
    if (state.transactions.length > 0) {
        const amounts = state.transactions.map(t => t.amount || 0);
        const avg = amounts.reduce((a, b) => a + b, 0) / amounts.length;
        const max = Math.max(...amounts);
        
        elements.avgAmount.textContent = formatCurrency(avg);
        elements.maxAmount.textContent = formatCurrency(max);
    }
}

function updateCharts() {
    if (typeof DashboardCharts !== 'undefined' && state.transactions.length > 0) {
        DashboardCharts.updateChartsWithTransactions(state.transactions);
    }
}

// ==================== Transactions ====================
function renderTransactions(transactions) {
    if (!transactions || transactions.length === 0) {
        elements.transactionsBody.innerHTML = `
            <tr class="loading-row">
                <td colspan="7">
                    <div class="loading-spinner">
                        <i class="fas fa-spinner fa-spin"></i>
                        Waiting for transactions...
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    // Sort by timestamp (newest first)
    const sorted = [...transactions].sort((a, b) => {
        return new Date(b.timestamp) - new Date(a.timestamp);
    }).slice(0, MAX_TRANSACTIONS);
    
    const html = sorted.map((txn, index) => {
        const isFraud = txn.is_fraud;
        const riskScore = Math.round((txn.fraud_probability || 0) * 100);
        const riskClass = getRiskClass(riskScore);
        
        return `
            <tr class="${isFraud ? 'fraud-row' : ''} ${index === 0 ? 'new-row' : ''}">
                <td><span class="transaction-id">${txn.transaction_id || 'N/A'}</span></td>
                <td>${txn.user_id || 'N/A'}</td>
                <td class="amount">${formatCurrency(txn.amount || 0)}</td>
                <td>${txn.merchant || 'N/A'}</td>
                <td>${formatTimeAgo(txn.timestamp)}</td>
                <td>
                    <span class="status-badge ${isFraud ? 'fraud' : 'normal'}">
                        <i class="fas ${isFraud ? 'fa-exclamation-triangle' : 'fa-check'}"></i>
                        ${isFraud ? 'Fraud' : 'Normal'}
                    </span>
                </td>
                <td>
                    <div class="risk-score">
                        <div class="risk-bar">
                            <div class="risk-bar-fill ${riskClass}" style="width: ${riskScore}%"></div>
                        </div>
                        <span class="risk-value ${riskClass}">${riskScore}%</span>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
    
    elements.transactionsBody.innerHTML = html;
}

function getRiskClass(score) {
    if (score >= 70) return 'high';
    if (score >= 40) return 'medium';
    return 'low';
}

// ==================== Alerts ====================
function renderAlerts(alerts) {
    if (!alerts || alerts.length === 0) {
        elements.alertsContainer.innerHTML = `
            <div class="no-alerts">
                <i class="fas fa-check-circle"></i>
                <p>No fraud alerts detected</p>
            </div>
        `;
        return;
    }
    
    const html = alerts.slice(0, MAX_ALERTS).map(alert => {
        const severity = alert.risk_level || (alert.amount > 5000 ? 'critical' : 'high');
        
        return `
            <div class="alert-card">
                <div class="alert-header">
                    <span class="alert-title">
                        <i class="fas fa-exclamation-triangle"></i>
                        Fraud Detected
                    </span>
                    <span class="alert-severity ${severity}">${severity}</span>
                </div>
                <div class="alert-details">
                    <div class="alert-detail">
                        <span class="alert-detail-label">Transaction ID:</span>
                        <span class="alert-detail-value">${alert.transaction_id}</span>
                    </div>
                    <div class="alert-detail">
                        <span class="alert-detail-label">User:</span>
                        <span class="alert-detail-value">${alert.user_id}</span>
                    </div>
                    <div class="alert-detail">
                        <span class="alert-detail-label">Amount:</span>
                        <span class="alert-detail-value">${formatCurrency(alert.amount)}</span>
                    </div>
                </div>
                ${alert.reasons && alert.reasons.length > 0 ? `
                    <div class="alert-reason">
                        <i class="fas fa-info-circle"></i>
                        ${alert.reasons.join(', ')}
                    </div>
                ` : ''}
                <div class="alert-time">
                    <i class="fas fa-clock"></i>
                    ${formatTimeAgo(alert.alert_time || alert.timestamp)}
                </div>
            </div>
        `;
    }).join('');
    
    elements.alertsContainer.innerHTML = html;
    elements.alertBadge.textContent = alerts.length;
}

let previousAlertCount = 0;

function checkForNewAlerts(alerts) {
    if (alerts.length > previousAlertCount && previousAlertCount > 0) {
        const newAlerts = alerts.slice(0, alerts.length - previousAlertCount);
        newAlerts.forEach(alert => {
            showNotification('fraud', 'Fraud Alert!', 
                `${alert.transaction_id}: ${formatCurrency(alert.amount)}`);
        });
    }
    previousAlertCount = alerts.length;
}

// ==================== Notifications ====================
function showNotification(type, title, message) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <i class="fas ${type === 'fraud' ? 'fa-exclamation-triangle' : 'fa-check-circle'} notification-icon"></i>
        <div class="notification-content">
            <div class="notification-title">${title}</div>
            <div class="notification-message">${message}</div>
        </div>
        <button class="notification-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    elements.notificationContainer.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

// ==================== Auto Refresh ====================
let refreshIntervalId = null;

function startAutoRefresh() {
    if (refreshIntervalId) {
        clearInterval(refreshIntervalId);
    }
    
    refreshIntervalId = setInterval(() => {
        loadDashboardData();
    }, REFRESH_INTERVAL);
    
    console.log(`Auto-refresh started: every ${REFRESH_INTERVAL/1000} seconds`);
}

function stopAutoRefresh() {
    if (refreshIntervalId) {
        clearInterval(refreshIntervalId);
        refreshIntervalId = null;
    }
}

// Manual refresh function
function refreshTransactions() {
    loadDashboardData();
    showNotification('success', 'Refreshed', 'Dashboard data updated');
}

// ==================== Utilities ====================
function formatNumber(num) {
    return num.toLocaleString('en-US');
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function formatTimeAgo(timestamp) {
    if (!timestamp) return 'N/A';
    
    try {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        // Less than 1 minute
        if (diff < 60000) {
            return 'Just now';
        }
        // Less than 1 hour
        if (diff < 3600000) {
            const mins = Math.floor(diff / 60000);
            return `${mins}m ago`;
        }
        // Less than 24 hours
        if (diff < 86400000) {
            const hours = Math.floor(diff / 3600000);
            return `${hours}h ago`;
        }
        // Otherwise show date and time
        return date.toLocaleDateString() + ' ' + 
               date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
        return timestamp;
    }
}

function updateClock() {
    const now = new Date();
    elements.currentTime.textContent = now.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
    });
}

// ==================== Error Handling ====================
window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
});

// Handle unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
});

// Export functions for global use
window.refreshTransactions = refreshTransactions;
window.DashboardApp = {
    loadDashboardData,
    refreshTransactions,
    showNotification
};

