// Fraud Detection Dashboard - JavaScript

const API_BASE_URL = 'http://localhost:5000/api';
let autoRefreshEnabled = true;
let refreshInterval = 3000; // 3 seconds

// DOM Elements
const elements = {
    connectionStatus: document.getElementById('connection-status'),
    statusDot: document.querySelector('.status-dot'),
    totalTransactions: document.getElementById('total-transactions'),
    fraudTransactions: document.getElementById('fraud-transactions'),
    fraudPercentage: document.getElementById('fraud-percentage'),
    activeAlerts: document.getElementById('active-alerts'),
    transactionsBody: document.getElementById('transactions-body'),
    alertsContainer: document.getElementById('alerts-container'),
    alertCount: document.getElementById('alert-count'),
    autoRefreshToggle: document.getElementById('auto-refresh')
};

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    checkConnection();
    loadDashboardData();
    setupAutoRefresh();
});

// Check API connection
async function checkConnection() {
    try {
        const response = await fetch(`${API_BASE_URL}/`);
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
    if (connected) {
        elements.connectionStatus.textContent = 'Connected';
        elements.statusDot.classList.add('connected');
    } else {
        elements.connectionStatus.textContent = 'Disconnected';
        elements.statusDot.classList.remove('connected');
    }
}

// Load all dashboard data
async function loadDashboardData() {
    try {
        await Promise.all([
            loadStats(),
            loadTransactions(),
            loadAlerts()
        ]);
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

// Load statistics
async function loadStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/stats`);
        const data = await response.json();
        
        if (data.success) {
            const stats = data.stats;
            elements.totalTransactions.textContent = formatNumber(stats.total_transactions);
            elements.fraudTransactions.textContent = formatNumber(stats.fraud_transactions);
            elements.fraudPercentage.textContent = `${stats.fraud_percentage}%`;
            elements.activeAlerts.textContent = stats.new_alerts;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load recent transactions
async function loadTransactions() {
    try {
        const response = await fetch(`${API_BASE_URL}/recent-transactions?limit=20`);
        const data = await response.json();
        
        if (data.success && data.transactions.length > 0) {
            renderTransactions(data.transactions);
        } else {
            renderTransactions([]);
        }
    } catch (error) {
        console.error('Error loading transactions:', error);
        elements.transactionsBody.innerHTML = `
            <tr class="loading">
                <td colspan="6">Error loading transactions</td>
            </tr>
        `;
    }
}

// Render transactions table
function renderTransactions(transactions) {
    if (transactions.length === 0) {
        elements.transactionsBody.innerHTML = `
            <tr class="loading">
                <td colspan="6">No transactions yet</td>
            </tr>
        `;
        return;
    }
    
    const html = transactions.map(txn => `
        <tr class="${txn.is_fraud ? 'fraud-row' : ''}">
            <td><code>${txn.transaction_id || 'N/A'}</code></td>
            <td>${txn.user_id || 'N/A'}</td>
            <td class="amount">$${formatNumber(txn.amount || 0)}</td>
            <td>${txn.location || 'N/A'}</td>
            <td>${formatTime(txn.timestamp)}</td>
            <td>
                <span class="status-badge ${txn.is_fraud ? 'fraud' : 'normal'}">
                    ${txn.is_fraud ? '⚠️ Fraud' : '✓ Normal'}
                </span>
            </td>
        </tr>
    `).join('');
    
    elements.transactionsBody.innerHTML = html;
}

// Load fraud alerts
async function loadAlerts() {
    try {
        const response = await fetch(`${API_BASE_URL}/alerts?limit=10`);
        const data = await response.json();
        
        if (data.success) {
            renderAlerts(data.alerts);
            elements.alertCount.textContent = data.count;
        }
    } catch (error) {
        console.error('Error loading alerts:', error);
    }
}

// Render alerts
function renderAlerts(alerts) {
    if (alerts.length === 0) {
        elements.alertsContainer.innerHTML = `
            <div class="no-alerts">No fraud alerts detected</div>
        `;
        return;
    }
    
    const html = alerts.map(alert => `
        <div class="alert-card">
            <h4>🚨 Fraud Detected</h4>
            <p><strong>Transaction:</strong> ${alert.transaction_id}</p>
            <p><strong>User:</strong> ${alert.user_id}</p>
            <p><strong>Amount:</strong> $${formatNumber(alert.amount)}</p>
            <p class="alert-time">${formatTime(alert.alert_time)}</p>
        </div>
    `).join('');
    
    elements.alertsContainer.innerHTML = html;
}

// Manual refresh button
function refreshTransactions() {
    loadDashboardData();
}

// Auto refresh setup
function setupAutoRefresh() {
    elements.autoRefreshToggle.addEventListener('change', (e) => {
        autoRefreshEnabled = e.target.checked;
    });
    
    // Set up interval
    setInterval(() => {
        if (autoRefreshEnabled) {
            loadDashboardData();
        }
    }, refreshInterval);
}

// Format number with commas
function formatNumber(num) {
    return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Format timestamp
function formatTime(timestamp) {
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
        // Otherwise show date
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
        return timestamp;
    }
}

// Error handling
window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
});

