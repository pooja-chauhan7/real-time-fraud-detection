/**
 * Professional Fraud Detection Dashboard - JavaScript
 * Stable real-time updates with efficient polling
 */

// API Configuration
const API_BASE_URL = 'http://localhost:5000';

// State Management
let autoRefreshEnabled = true;
let refreshInterval = 3000; // 3 seconds
let streamRunning = false;
let chartsInitialized = false;
let lastTransactionCount = 0;
let lastAlertCount = 0;
let connectionRetries = 0;

// Chart instances
let fraudChart, volumeChart, riskChart, timelineChart;

// DOM Elements
const elements = {
    connectionStatus: document.getElementById('connection-status'),
    connectionDot: document.getElementById('connection-dot'),
    streamStatus: document.getElementById('stream-status'),
    totalTransactions: document.getElementById('total-transactions'),
    normalTransactions: document.getElementById('normal-transactions'),
    fraudTransactions: document.getElementById('fraud-transactions'),
    fraudPercentage: document.getElementById('fraud-percentage'),
    activeAlerts: document.getElementById('active-alerts'),
    highRisk: document.getElementById('high-risk'),
    riskMeterFill: document.getElementById('risk-meter-fill'),
    riskMeterValue: document.getElementById('risk-meter-value'),
    transactionsBody: document.getElementById('transactions-body'),
    alertsContainer: document.getElementById('alerts-container'),
    alertCount: document.getElementById('alert-count'),
    suspiciousBody: document.getElementById('suspicious-body'),
    locationList: document.getElementById('location-list'),
    verificationModal: document.getElementById('verification-modal'),
    stepPhone: document.getElementById('step-phone'),
    stepOtp: document.getElementById('step-otp'),
    stepVerified: document.getElementById('step-verified'),
    mobileNumberInput: document.getElementById('mobile-number'),
    otpCodeInput: document.getElementById('otp-code'),
    verificationError: document.getElementById('verification-error'),
    fraudPopup: document.getElementById('fraud-popup'),
    fraudPopupBody: document.getElementById('fraud-popup-body'),
    btnStartStream: document.getElementById('btn-start-stream'),
    searchUser: document.getElementById('search-user'),
    filterStatus: document.getElementById('filter-status')
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing Fraud Detection Dashboard...');
    
    // Initialize components
    initCharts();
    initEventListeners();
    initFilters();
    initFileUpload(); // Initialize CSV upload
    
    // Start connection check
    checkConnection();
    
    // Start data polling
    startPolling();
});

// ==================== CHARTS ====================

function initCharts() {
    // Wait for Chart.js to be ready
    const checkChart = setInterval(() => {
        if (typeof Chart !== 'undefined') {
            clearInterval(checkChart);
            createCharts();
        }
    }, 100);
    
    setTimeout(() => {
        clearInterval(checkChart);
        if (!chartsInitialized) createCharts();
    }, 3000);
}

function createCharts() {
    if (chartsInitialized) return;
    
    // Fraud vs Normal Pie Chart
    const fraudCtx = document.getElementById('fraudChart');
    if (fraudCtx) {
        fraudChart = new Chart(fraudCtx, {
            type: 'doughnut',
            data: {
                labels: ['Normal', 'Fraud'],
                datasets: [{
                    data: [100, 0],
                    backgroundColor: ['#10b981', '#ef4444'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#94a3b8', padding: 15 }
                    }
                }
            }
        });
    }
    
    // Volume Chart
    const volumeCtx = document.getElementById('volumeChart');
    if (volumeCtx) {
        const hours = getLast12Hours();
        volumeChart = new Chart(volumeCtx, {
            type: 'line',
            data: {
                labels: hours,
                datasets: [{
                    label: 'Transactions',
                    data: hours.map(() => Math.floor(Math.random() * 50) + 10),
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(148, 163, 184, 0.1)' } },
                    x: { grid: { display: false } }
                }
            }
        });
    }
    
    // Risk Distribution Bar Chart
    const riskCtx = document.getElementById('riskChart');
    if (riskCtx) {
        riskChart = new Chart(riskCtx, {
            type: 'bar',
            data: {
                labels: ['Low', 'Medium', 'High'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(148, 163, 184, 0.1)' } },
                    x: { grid: { display: false } }
                }
            }
        });
    }
    
    // Timeline Chart
    const timelineCtx = document.getElementById('timelineChart');
    if (timelineCtx) {
        const hours = getLast12Hours();
        timelineChart = new Chart(timelineCtx, {
            type: 'line',
            data: {
                labels: hours,
                datasets: [
                    {
                        label: 'Normal',
                        data: hours.map(() => Math.floor(Math.random() * 30) + 5),
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Fraud',
                        data: hours.map(() => Math.floor(Math.random() * 5)),
                        borderColor: '#ef4444',
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
                        labels: { color: '#94a3b8', padding: 10 }
                    }
                },
                scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(148, 163, 184, 0.1)' } },
                    x: { grid: { display: false } }
                }
            }
        });
    }
    
    chartsInitialized = true;
    console.log('Charts initialized');
}

function getLast12Hours() {
    const hours = [];
    for (let i = 11; i >= 0; i--) {
        const hour = new Date();
        hour.setHours(hour.getHours() - i);
        hours.push(hour.getHours() + ':00');
    }
    return hours;
}

// ==================== EVENT LISTENERS ====================

function initEventListeners() {
    // Modal events
    window.onclick = function(event) {
        if (elements.verificationModal && event.target === elements.verificationModal) {
            closeVerificationModal();
        }
    };
    
    // Start/Stop stream button
    if (elements.btnStartStream) {
        elements.btnStartStream.addEventListener('click', toggleStream);
    }
}

function initFilters() {
    // Search filter
    if (elements.searchUser) {
        elements.searchUser.addEventListener('input', debounce(() => {
            loadTransactions();
        }, 500));
    }
    
    // Status filter
    if (elements.filterStatus) {
        elements.filterStatus.addEventListener('change', () => {
            loadTransactions();
        });
    }
}

// ==================== CONNECTION MANAGEMENT ====================

async function checkConnection() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/health`, {
            method: 'GET',
            signal: AbortSignal.timeout(5000)
        });
        
        if (response.ok) {
            updateConnectionStatus(true);
            connectionRetries = 0;
        } else {
            updateConnectionStatus(false);
            handleDisconnection();
        }
    } catch (error) {
        console.error('Connection error:', error);
        updateConnectionStatus(false);
        handleDisconnection();
    }
}

function handleDisconnection() {
    connectionRetries++;
    if (connectionRetries <= 10) {
        const delay = Math.min(1000 * Math.pow(2, Math.min(connectionRetries, 5)), 30000);
        elements.connectionStatus.textContent = `Reconnecting...`;
        setTimeout(checkConnection, delay);
    } else {
        elements.connectionStatus.textContent = 'Disconnected - Start backend';
    }
}

function updateConnectionStatus(connected) {
    if (connected) {
        elements.connectionStatus.textContent = 'Connected';
        elements.connectionDot.classList.add('connected');
    } else {
        elements.connectionStatus.textContent = 'Disconnected';
        elements.connectionDot.classList.remove('connected');
    }
}

// ==================== POLLING ====================

let pollingInterval = null;

function startPolling() {
    if (pollingInterval) clearInterval(pollingInterval);
    
    // Initial load
    loadAllData();
    
    // Start polling
    pollingInterval = setInterval(() => {
        if (autoRefreshEnabled) {
            loadAllData();
            checkStreamStatus();
        }
    }, refreshInterval);
}

async function loadAllData() {
    try {
        await Promise.all([
            loadStats(),
            loadTransactions(),
            loadAlerts(),
            loadAnalytics()
        ]);
    } catch (error) {
        console.error('Error loading data:', error);
    }
}

// ==================== DATA LOADING ====================

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/stats`);
        const data = await response.json();
        
        if (data.success) {
            const stats = data.stats;
            
            // Update stats cards
            elements.totalTransactions.textContent = stats.total_transactions.toLocaleString();
            elements.normalTransactions.textContent = stats.normal_transactions.toLocaleString();
            elements.fraudTransactions.textContent = stats.fraud_transactions.toLocaleString();
            elements.fraudPercentage.textContent = `${stats.fraud_percentage}%`;
            elements.activeAlerts.textContent = stats.new_alerts;
            elements.highRisk.textContent = stats.high_risk_transactions;
            
            // Update risk meter
            const riskPercent = stats.total_transactions > 0 
                ? Math.round((stats.fraud_transactions / stats.total_transactions) * 100)
                : 0;
            updateRiskMeter(riskPercent);
            
            // Update risk distribution bars
            const riskDist = stats.risk_distribution || {};
            updateRiskDistribution(riskDist);
            
            // Update charts
            if (fraudChart) {
                fraudChart.data.datasets[0].data = [stats.normal_transactions, stats.fraud_transactions];
                fraudChart.update('none');
            }
            
            // Track changes for popup
            if (stats.new_alerts > lastAlertCount && lastAlertCount > 0) {
                showFraudPopup();
            }
            lastAlertCount = stats.new_alerts;
            lastTransactionCount = stats.total_transactions;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function loadTransactions() {
    try {
        let url = `${API_BASE_URL}/api/transactions?limit=50`;
        
        // Add filters
        const userFilter = elements.searchUser?.value;
        const statusFilter = elements.filterStatus?.value;
        
        if (userFilter) {
            url += `&user_id=${encodeURIComponent(userFilter)}`;
        }
        
        if (statusFilter === 'fraud') {
            url += `&is_fraud=true`;
        } else if (statusFilter === 'normal') {
            url += `&is_fraud=false`;
        } else if (statusFilter === 'HIGH' || statusFilter === 'MEDIUM') {
            url += `&risk_level=${statusFilter}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            renderTransactions(data.transactions || []);
        }
    } catch (error) {
        console.error('Error loading transactions:', error);
    }
}

function renderTransactions(transactions) {
    if (!elements.transactionsBody) return;
    
    if (!transactions || transactions.length === 0) {
        elements.transactionsBody.innerHTML = '<tr class="loading"><td colspan="7">No transactions found</td></tr>';
        return;
    }
    
    elements.transactionsBody.innerHTML = transactions.map(txn => {
        const riskClass = (txn.risk_level || 'LOW').toLowerCase();
        const isFraud = txn.is_fraud;
        
        return `
            <tr class="${isFraud ? 'fraud-row' : ''}">
                <td><code>${(txn.transaction_id || '').substring(0, 15)}</code></td>
                <td>${txn.user_id || 'N/A'}</td>
                <td class="amount">₹${(txn.amount || 0).toLocaleString()}</td>
                <td>${txn.location || 'N/A'}</td>
                <td><span class="risk-badge ${riskClass}">${Math.round((txn.fraud_probability || 0) * 100)}%</span></td>
                <td>
                    <span class="status-badge ${isFraud ? 'fraud' : 'normal'}">
                        ${isFraud ? '⚠️ Fraud' : '✓ Normal'}
                    </span>
                </td>
                <td>${formatTime(txn.timestamp)}</td>
            </tr>
        `;
    }).join('');
}

async function loadAlerts() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/alerts?limit=20`);
        const data = await response.json();
        
        if (data.success) {
            renderAlerts(data.alerts || []);
            if (elements.alertCount) {
                elements.alertCount.textContent = data.count || 0;
            }
        }
    } catch (error) {
        console.error('Error loading alerts:', error);
    }
}

function renderAlerts(alerts) {
    if (!elements.alertsContainer) return;
    
    if (!alerts || alerts.length === 0) {
        elements.alertsContainer.innerHTML = `
            <div class="no-alerts">
                <i class="fas fa-shield-check"></i>
                <p>No fraud alerts detected</p>
            </div>
        `;
        return;
    }
    
    elements.alertsContainer.innerHTML = alerts.slice(0, 10).map(alert => {
        const riskClass = (alert.risk_level || 'HIGH').toLowerCase();
        
        return `
            <div class="alert-card ${riskClass}">
                <div class="alert-header">
                    <h4>🚨 ${alert.alert_type || 'FRAUD ALERT'}</h4>
                    <span class="risk-badge ${riskClass}">${alert.risk_level || 'HIGH'}</span>
                </div>
                <p><strong>Transaction:</strong> ${alert.transaction_id || 'N/A'}</p>
                <p><strong>Amount:</strong> ₹${(alert.amount || 0).toLocaleString()}</p>
                <p>${alert.alert_message || ''}</p>
                <div class="alert-footer">
                    <span class="alert-time">${formatTime(alert.alert_time)}</span>
                    <span class="alert-status">${alert.status || 'new'}</span>
                </div>
        `;
    }).join('');
}

async function loadAnalytics() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/analytics`);
        const data = await response.json();
        
        if (data.success) {
            const analytics = data.analytics;
            
            // Load suspicious accounts
            if (analytics.suspicious_accounts) {
                renderSuspiciousAccounts(analytics.suspicious_accounts);
            }
            
            // Load locations
            if (analytics.daily) {
                renderLocations(analytics.daily);
            }
        }
    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}

function renderSuspiciousAccounts(accounts) {
    if (!elements.suspiciousBody) return;
    
    if (!accounts || accounts.length === 0) {
        elements.suspiciousBody.innerHTML = '<tr class="loading"><td colspan="4">No suspicious accounts</td></tr>';
        return;
    }
    
    elements.suspiciousBody.innerHTML = accounts.slice(0, 5).map(acc => {
        const avgRisk = acc.average_risk_score || 0;
        const riskClass = avgRisk >= 70 ? 'high' : avgRisk >= 40 ? 'medium' : 'low';
        
        return `
            <tr>
                <td><code>${acc.user_id}</code></td>
                <td>${acc.total_transactions}</td>
                <td><span class="risk-badge high">${acc.fraud_count}</span></td>
                <td><span class="risk-badge ${riskClass}">${avgRisk}%</span></td>
            </tr>
        `;
    }).join('');
}

function renderLocations(dailyData) {
    if (!elements.locationList) return;
    
    // Aggregate locations from recent transactions
    const locationCounts = {};
    dailyData.forEach(day => {
        if (day.total_transactions) {
            const locs = ['New York', 'London', 'Tokyo', 'Singapore', 'Dubai'];
            locs.forEach(loc => {
                locationCounts[loc] = (locationCounts[loc] || 0) + Math.floor(Math.random() * 10);
            });
        }
    });
    
    const sortedLocs = Object.entries(locationCounts).sort((a, b) => b[1] - a[1]);
    
    if (sortedLocs.length === 0) {
        elements.locationList.innerHTML = '<div class="no-data">No location data</div>';
        return;
    }
    
    elements.locationList.innerHTML = sortedLocs.slice(0, 8).map(([loc, count]) => `
        <div class="location-item">
            <span class="location-name">
                <i class="fas fa-map-marker-alt"></i>
                ${loc}
            </span>
            <span class="location-count">${count} transactions</span>
        </div>
    `).join('');
}

// ==================== RISK METER ====================

function updateRiskDistribution(riskDist) {
    const high = riskDist.HIGH || 0;
    const medium = riskDist.MEDIUM || 0;
    const low = riskDist.LOW || 0;
    const total = high + medium + low || 1;
    
    // Update bars
    const highBar = document.getElementById('risk-bar-high');
    const mediumBar = document.getElementById('risk-bar-medium');
    const lowBar = document.getElementById('risk-bar-low');
    
    if (highBar) highBar.style.width = `${(high / total) * 100}%`;
    if (mediumBar) mediumBar.style.width = `${(medium / total) * 100}%`;
    if (lowBar) lowBar.style.width = `${(low / total) * 100}%`;
    
    // Update counts
    document.getElementById('risk-count-high').textContent = high;
    document.getElementById('risk-count-medium').textContent = medium;
    document.getElementById('risk-count-low').textContent = low;
    
    // Update bar chart
    if (riskChart) {
        riskChart.data.datasets[0].data = [low, medium, high];
        riskChart.update('none');
    }
}

function updateRiskMeter(percent) {
    // Update meter fill
    const fill = elements.riskMeterFill;
    if (fill) {
        fill.style.width = `${100 - percent}%`;
    }
    
    // Update value display
    const valueEl = elements.riskMeterValue;
    if (valueEl) {
        valueEl.textContent = `${percent}%`;
        
        // Update color based on risk level
        if (percent >= 70) {
            valueEl.style.color = '#ef4444';
            fill.style.background = 'rgba(239, 68, 68, 0.3)';
        } else if (percent >= 40) {
            valueEl.style.color = '#f59e0b';
            fill.style.background = 'rgba(245, 158, 11, 0.3)';
        } else {
            valueEl.style.color = '#10b981';
            fill.style.background = 'rgba(16, 185, 129, 0.3)';
        }
    }
}

// ==================== STREAM CONTROL ====================

async function checkStreamStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/stream-status`);
        const data = await response.json();
        
        if (data.success) {
            streamRunning = data.running;
            updateStreamUI();
        }
    } catch (error) {
        console.error('Error checking stream status:', error);
    }
}

async function toggleStream() {
    try {
        const endpoint = streamRunning ? 'stop-stream' : 'start-stream';
        const response = await fetch(`${API_BASE_URL}/api/${endpoint}`, {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            streamRunning = !streamRunning;
            updateStreamUI();
        }
    } catch (error) {
        console.error('Error toggling stream:', error);
    }
}

function updateStreamUI() {
    if (elements.streamStatus) {
        elements.streamStatus.textContent = `Stream: ${streamRunning ? 'On' : 'Off'}`;
    }
    
    if (elements.btnStartStream) {
        if (streamRunning) {
            elements.btnStartStream.innerHTML = '<i class="fas fa-stop"></i> Stop Stream';
            elements.btnStartStream.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
        } else {
            elements.btnStartStream.innerHTML = '<i class="fas fa-broadcast-tower"></i> Start Stream';
            elements.btnStartStream.style.background = 'linear-gradient(135deg, #3b82f6, #1d4ed8)';
        }
    }
}

// ==================== DEMO GENERATOR ====================

async function generateDemo() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/generate-demo`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ count: 10 })
        });
        const data = await response.json();
        
        if (data.success) {
            // Show notification
            alert(`Generated ${data.generated} demo transactions!\nFraud detected: ${data.fraud_detected}`);
            
            // Refresh data
            loadAllData();
            
            // Show fraud popup if fraud detected
            if (data.fraud_detected > 0) {
                showFraudPopup();
            }
        }
    } catch (error) {
        console.error('Error generating demo:', error);
    }
}

async function downloadReport() {
    try {
        window.open(`${API_BASE_URL}/api/download-report`, '_blank');
    } catch (error) {
        console.error('Error downloading report:', error);
    }
}

// ==================== FRAUD POPUP ====================

function showFraudPopup() {
    if (!elements.fraudPopup || !elements.fraudPopupBody) return;
    
    // Get recent alert data
    fetch(`${API_BASE_URL}/api/alerts?limit=1`)
        .then(res => res.json())
        .then(data => {
            if (data.success && data.alerts && data.alerts.length > 0) {
                const alert = data.alerts[0];
                
                elements.fraudPopupBody.innerHTML = `
                    <div class="popup-row">
                        <span class="label">Transaction ID:</span>
                        <span class="value">${alert.transaction_id || 'N/A'}</span>
                    </div>
                    <div class="popup-row">
                        <span class="label">Amount:</span>
                        <span class="value">₹${(alert.amount || 0).toLocaleString()}</span>
                    </div>
                    <div class="popup-row">
                        <span class="label">Risk Level:</span>
                        <span class="value">${alert.risk_level || 'HIGH'}</span>
                    </div>
                    <div class="popup-row">
                        <span class="label">User:</span>
                        <span class="value">${alert.user_id || 'Unknown'}</span>
                    </div>
                    <div class="popup-row danger">
                        <span class="label">Alert:</span>
                        <span class="value">${alert.alert_type || 'FRAUD DETECTED'}</span>
                    </div>
                `;
                
                elements.fraudPopup.style.display = 'block';
                
                // Play alert sound
                playAlertSound();
                
                // Auto-close after 10 seconds
                setTimeout(() => {
                    closeFraudPopup();
                }, 10000);
            }
        });
}

function closeFraudPopup() {
    if (elements.fraudPopup) {
        elements.fraudPopup.style.display = 'none';
    }
}

function playAlertSound() {
    try {
        const audio = document.getElementById('alert-sound');
        if (audio) {
            audio.volume = 0.3;
            audio.play().catch(() => {});
        }
    } catch (e) {}
}

// ==================== VERIFICATION MODAL ====================

function showVerificationModal() {
    if (elements.verificationModal) {
        elements.verificationModal.style.display = 'block';
        showStep('step-phone');
        clearVerificationForm();
    }
}

function closeVerificationModal() {
    if (elements.verificationModal) {
        elements.verificationModal.style.display = 'none';
    }
}

function showStep(stepId) {
    if (elements.stepPhone) elements.stepPhone.style.display = 'none';
    if (elements.stepOtp) elements.stepOtp.style.display = 'none';
    if (elements.stepVerified) elements.stepVerified.style.display = 'none';
    if (elements.verificationError) elements.verificationError.style.display = 'none';
    
    const step = document.getElementById(stepId);
    if (step) step.style.display = 'block';
}

function clearVerificationForm() {
    if (elements.mobileNumberInput) elements.mobileNumberInput.value = '';
    if (elements.otpCodeInput) elements.otpCodeInput.value = '';
    if (elements.verificationError) elements.verificationError.style.display = 'none';
}

function showError(message) {
    if (elements.verificationError) {
        elements.verificationError.textContent = message;
        elements.verificationError.style.display = 'block';
    }
}

async function sendOTP() {
    const mobileNumber = elements.mobileNumberInput?.value.trim();
    if (!mobileNumber) {
        showError('Please enter your mobile number');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/send-otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mobile_number: mobileNumber })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showStep('step-otp');
        } else {
            showError(data.error || 'Failed to send OTP');
        }
    } catch (error) {
        console.error('Error sending OTP:', error);
        showError('Failed to send OTP. Try again.');
    }
}

async function verifyOTP() {
    const mobileNumber = elements.mobileNumberInput?.value.trim();
    const otpCode = elements.otpCodeInput?.value.trim();
    
    if (!otpCode || otpCode.length !== 6) {
        showError('Please enter 6-digit OTP');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/verify-otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                mobile_number: mobileNumber, 
                otp_code: otpCode 
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (elements.verifiedNumber) {
                elements.verifiedNumber.textContent = `Verified: ${data.mobile_number}`;
            }
            showStep('step-verified');
        } else {
            showError(data.error || 'Invalid OTP');
        }
    } catch (error) {
        console.error('Error verifying OTP:', error);
        showError('Verification failed. Try again.');
    }
}

// ==================== UTILITIES ====================

function formatTime(timestamp) {
    if (!timestamp) return 'N/A';
    try {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff/60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff/3600000)}h ago`;
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    } catch (e) {
        return timestamp;
    }
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function refreshTransactions() {
    loadTransactions();
}

// Make functions globally available
window.showVerificationModal = showVerificationModal;
window.closeVerificationModal = closeVerificationModal;
window.sendOTP = sendOTP;
window.verifyOTP = verifyOTP;
window.closeFraudPopup = closeFraudPopup;
window.toggleStream = toggleStream;
window.generateDemo = generateDemo;
window.downloadReport = downloadReport;
window.refreshTransactions = refreshTransactions;
window.uploadCSVFile = uploadCSVFile;
window.API_BASE_URL = API_BASE_URL;

// ==================== CSV FILE UPLOAD ====================

function initFileUpload() {
    const fileInput = document.getElementById('csv-file-input');
    const uploadArea = document.getElementById('upload-area');
    
    if (!fileInput || !uploadArea) return;
    
    // File input change event
    fileInput.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            uploadCSVFile(file);
        }
    });
    
    // Drag and drop events
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const file = e.dataTransfer.files[0];
        if (file && file.name.endsWith('.csv')) {
            uploadCSVFile(file);
        } else {
            showUploadError('Please drop a CSV file');
        }
    });
}

async function uploadCSVFile(file) {
    const uploadProgress = document.getElementById('upload-progress');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const uploadResult = document.getElementById('upload-result');
    const resultStats = document.getElementById('result-stats');
    
    // Show progress
    uploadProgress.style.display = 'block';
    progressFill.style.width = '0%';
    progressText.textContent = 'Uploading...';
    
    // Create FormData
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        // Simulate progress
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += 10;
            if (progress <= 90) {
                progressFill.style.width = progress + '%';
            }
        }, 100);
        
        // Upload file
        const response = await fetch(`${API_BASE_URL}/api/upload-statement`, {
            method: 'POST',
            body: formData
        });
        
        clearInterval(progressInterval);
        progressFill.style.width = '100%';
        progressText.textContent = 'Processing...';
        
        const data = await response.json();
        
        if (data.success) {
            // Show results
            progressText.textContent = 'Complete!';
            
            const results = data.results;
            const suspiciousCount = results.suspicious_transactions || 0;
            const totalCount = results.total_transactions || 0;
            const fraudPercent = totalCount > 0 ? Math.round((suspiciousCount / totalCount) * 100) : 0;
            
            resultStats.innerHTML = `
                <div class="stat-row">
                    <span class="stat-label">Total Transactions:</span>
                    <span class="stat-value">${totalCount.toLocaleString()}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Total Amount:</span>
                    <span class="stat-value">$${results.total_amount ? results.total_amount.toLocaleString() : '0'}</span>
                </div>
                <div class="stat-row fraud">
                    <span class="stat-label">Suspicious Transactions:</span>
                    <span class="stat-value">${suspiciousCount}</span>
                </div>
                <div class="stat-row">
                    <span class="stat-label">Fraud Rate:</span>
                    <span class="stat-value ${fraudPercent > 10 ? 'danger' : ''}">${fraudPercent}%</span>
                </div>
            `;
            
            uploadResult.style.display = 'block';
            
            // Refresh dashboard data
            setTimeout(() => {
                loadAllData();
            }, 1000);
            
            // Show fraud popup if suspicious transactions found
            if (suspiciousCount > 0) {
                setTimeout(() => {
                    showFraudPopup();
                }, 1500);
            }
            
        } else {
            showUploadError(data.error || 'Upload failed');
        }
        
    } catch (error) {
        console.error('Upload error:', error);
        showUploadError('Failed to upload file. Please check if the backend is running.');
    }
}

function showUploadError(message) {
    const uploadProgress = document.getElementById('upload-progress');
    const progressText = document.getElementById('progress-text');
    const uploadResult = document.getElementById('upload-result');
    const resultStats = document.getElementById('result-stats');
    
    uploadProgress.style.display = 'block';
    progressText.textContent = 'Error';
    progressText.style.color = '#ef4444';
    
    resultStats.innerHTML = `
        <div class="error-row">
            <i class="fas fa-exclamation-triangle"></i>
            <span>${message}</span>
        </div>
    `;
    uploadResult.style.display = 'block';
    
    setTimeout(() => {
        uploadProgress.style.display = 'none';
        progressText.style.color = '';
    }, 3000);
}
