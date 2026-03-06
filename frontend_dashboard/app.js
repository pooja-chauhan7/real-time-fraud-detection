/**
 * Fraud Detection Dashboard - JavaScript
 * Enhanced Version with Bank Statement Analyzer, Risk Scoring, and Analytics
 */

const API_BASE_URL = 'http://localhost:5000';
let autoRefreshEnabled = true;
let refreshInterval = 3000;
let streamStarted = false;
let connectionRetryCount = 0;
const MAX_RETRY_ATTEMPTS = 10;
let connectionCheckInterval = null;
let chartsInitialized = false;

// User state
let currentUser = {
    userId: null,
    username: null,
    isVerified: false,
    mobileNumber: null,
    email: null
};

// OTP state
let otpTimerInterval = null;
let otpExpiryTime = 0;
let canResendOTP = true;

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
    autoRefreshToggle: document.getElementById('auto-refresh'),
    verifiedBadge: document.getElementById('verified-badge'),
    btnVerify: document.getElementById('btn-verify'),
    verificationModal: document.getElementById('verification-modal'),
    stepPhone: document.getElementById('step-phone'),
    stepOtp: document.getElementById('step-otp'),
    stepVerified: document.getElementById('step-verified'),
    mobileNumberInput: document.getElementById('mobile-number'),
    otpCodeInput: document.getElementById('otp-code'),
    otpTimer: document.getElementById('otp-timer'),
    verificationError: document.getElementById('verification-error'),
    verifiedNumber: document.getElementById('verified-number')
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard initializing...');
    initTabs();
    initUpload();
    initAnalyzeForm();
    initCharts();
    checkConnection();
    loadCurrentUser();
    setupAutoRefresh();
    startLiveStream();
    connectionCheckInterval = setInterval(checkConnection, 10000);
});

// Initialize Charts
function initCharts() {
    // Wait for Chart.js to load
    const checkChart = setInterval(() => {
        if (typeof Chart !== 'undefined') {
            clearInterval(checkChart);
            initializeCharts();
        }
    }, 100);
    
    // Timeout after 5 seconds
    setTimeout(() => clearInterval(checkChart), 5000);
}

function initializeCharts() {
    if (chartsInitialized) return;
    
    // Transaction Type Doughnut Chart
    const typeCtx = document.getElementById('type-chart');
    if (typeCtx) {
        window.typeChart = new Chart(typeCtx, {
            type: 'doughnut',
            data: {
                labels: ['TRANSFER', 'UPI', 'CARD', 'INTERNATIONAL', 'CASH'],
                datasets: [{
                    data: [30, 25, 25, 15, 5],
                    backgroundColor: ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#3b82f6'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'bottom' }
                },
                cutout: '60%'
            }
        });
    }
    
    // Daily Trend Line Chart
    const dailyCtx = document.getElementById('daily-chart');
    if (dailyCtx) {
        const days = [];
        const totals = [];
        const frauds = [];
        
        for (let i = 6; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            days.push(date.toLocaleDateString('en-US', { weekday: 'short' }));
            totals.push(Math.floor(Math.random() * 50) + 20);
            frauds.push(Math.floor(Math.random() * 10) + 1);
        }
        
        window.dailyChart = new Chart(dailyCtx, {
            type: 'line',
            data: {
                labels: days,
                datasets: [
                    {
                        label: 'Total Transactions',
                        data: totals,
                        borderColor: '#4f46e5',
                        backgroundColor: 'rgba(79, 70, 229, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Fraudulent',
                        data: frauds,
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
                    legend: { position: 'bottom' }
                },
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    }
    
    chartsInitialized = true;
    console.log('Charts initialized');
}

// Tab Navigation
function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            
            // Update button states
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Update tab content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(tabId).classList.add('active');
            
            // Load data for specific tabs
            if (tabId === 'analytics') {
                loadAnalytics();
            }
        });
    });
}

// Upload Handler
function initUpload() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');
    
    if (!uploadArea || !fileInput) return;
    
    uploadArea.addEventListener('click', () => fileInput.click());
    
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });
    
    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });
    
    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) uploadFile(files[0]);
    });
    
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) uploadFile(e.target.files[0]);
    });
}

async function uploadFile(file) {
    if (!file.name.endsWith('.csv')) {
        alert('Please upload a CSV file');
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    const uploadArea = document.getElementById('upload-area');
    uploadArea.innerHTML = '<i class="fas fa-spinner fa-spin"></i><p>Analyzing transactions...</p>';
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/upload-statement`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayUploadResults(data.results);
            // Refresh dashboard data after upload
            loadDashboardData();
        } else {
            alert(data.error || 'Upload failed');
            initUpload(); // Reset upload area
        }
    } catch (error) {
        console.error('Upload error:', error);
        alert('Upload failed. Make sure backend is running at ' + API_BASE_URL);
        initUpload();
    }
}

function displayUploadResults(results) {
    const uploadResults = document.getElementById('upload-results');
    if (!uploadResults) return;
    
    uploadResults.style.display = 'block';
    
    const resultTotal = document.getElementById('result-total');
    const resultAmount = document.getElementById('result-amount');
    const resultSuspicious = document.getElementById('result-suspicious');
    
    if (resultTotal) resultTotal.textContent = results.total_transactions;
    if (resultAmount) resultAmount.textContent = `₹${results.total_amount.toLocaleString()}`;
    if (resultSuspicious) resultSuspicious.textContent = results.suspicious_transactions;
    
    // Display transactions
    const container = document.getElementById('result-transactions');
    if (container && results.transactions) {
        container.innerHTML = results.transactions.map(txn => `
            <div class="txn-item ${txn.is_fraud ? 'fraud' : ''}">
                <span class="txn-amount">₹${txn.amount.toLocaleString()}</span>
                <span class="txn-type">${txn.transaction_type || 'TRANSFER'}</span>
                <span class="txn-risk ${(txn.risk_level || 'LOW').toLowerCase()}">${txn.risk_level || 'LOW'}</span>
            </div>
        `).join('');
    }
    
    // Reset upload area
    const uploadArea = document.getElementById('upload-area');
    if (uploadArea) {
        uploadArea.innerHTML = `
            <i class="fas fa-cloud-upload-alt"></i>
            <h3>Upload Bank Statement (CSV)</h3>
            <p>Drag and drop your CSV file here or click to browse</p>
            <button class="btn-primary" onclick="document.getElementById('file-input').click()">
                <i class="fas fa-folder-open"></i> Select File
            </button>
        `;
    }
}

// Analyze Form
function initAnalyzeForm() {
    const form = document.getElementById('analyze-form');
    if (!form) return;
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const amount = parseFloat(document.getElementById('analyze-amount').value);
        const type = document.getElementById('analyze-type').value;
        const receiver = document.getElementById('analyze-receiver').value;
        const description = document.getElementById('analyze-description').value;
        
        const submitBtn = form.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analyzing...';
        submitBtn.disabled = true;
        
        try {
            const response = await fetch(`${API_BASE_URL}/api/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    amount: amount,
                    transaction_type: type,
                    receiver_account: receiver,
                    description: description
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                displayAnalysisResult(data.transaction, data.analysis);
                // Refresh dashboard after analysis
                loadDashboardData();
            } else {
                alert(data.error || 'Analysis failed');
            }
        } catch (error) {
            console.error('Analysis error:', error);
            alert('Analysis failed. Make sure backend is running.');
        } finally {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        }
    });
}

function displayAnalysisResult(transaction, analysis) {
    const resultDiv = document.getElementById('analysis-result');
    const contentDiv = document.getElementById('analysis-content');
    
    if (!resultDiv || !contentDiv) return;
    
    resultDiv.style.display = 'block';
    
    const riskClass = (analysis.risk_level || 'LOW').toLowerCase();
    const riskIcon = analysis.is_fraud ? 'fa-exclamation-triangle' : 'fa-check-circle';
    const riskColor = analysis.is_fraud ? '#e74c3c' : '#27ae60';
    
    contentDiv.innerHTML = `
        <div class="analysis-header">
            <i class="fas ${riskIcon}" style="color: ${riskColor}"></i>
            <span class="risk-badge ${riskClass}">${analysis.risk_level || 'LOW'} RISK</span>
        </div>
        <div class="analysis-details">
            <p><strong>Amount:</strong> ₹${transaction.amount.toLocaleString()}</p>
            <p><strong>Fraud Probability:</strong> ${(analysis.fraud_probability * 100).toFixed(1)}%</p>
            ${analysis.reasons && analysis.reasons.length > 0 ? 
                `<p><strong>Reasons:</strong></p><ul>${analysis.reasons.map(r => `<li>${r}</li>`).join('')}</ul>` : ''}
        </div>
    `;
}

// Analytics
async function loadAnalytics() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/analytics`);
        const data = await response.json();
        
        if (data.success) {
            displayAnalytics(data.analytics);
            updateChartsWithData(data.analytics);
        }
    } catch (error) {
        console.error('Error loading analytics:', error);
    }
}

function updateChartsWithData(analytics) {
    // Update transaction type chart
    if (window.typeChart && analytics.by_type && analytics.by_type.length > 0) {
        window.typeChart.data.labels = analytics.by_type.map(t => t.type);
        window.typeChart.data.datasets[0].data = analytics.by_type.map(t => t.count);
        window.typeChart.update();
    }
    
    // Update daily trend chart
    if (window.dailyChart && analytics.daily && analytics.daily.length > 0) {
        window.dailyChart.data.labels = analytics.daily.map(d => d.date);
        window.dailyChart.data.datasets[0].data = analytics.daily.map(d => d.total_transactions);
        window.dailyChart.data.datasets[1].data = analytics.daily.map(d => d.fraud_transactions);
        window.dailyChart.update();
    }
}

function displayAnalytics(analytics) {
    // Activity log
    const activityLog = document.getElementById('activity-log');
    if (activityLog && analytics.recent_activity) {
        activityLog.innerHTML = analytics.recent_activity.map(a => `
            <div class="activity-item">
                <span class="activity-time">${formatTime(a.timestamp)}</span>
                <span class="activity-type">${a.type || 'ACTIVITY'}</span>
                <span class="activity-desc">${a.description || ''}</span>
            </div>
        `).join('') || '<div class="no-activity">No recent activity</div>';
    }
}

// Connection Management
async function checkConnection() {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        const response = await fetch(`${API_BASE_URL}/api/`, { signal: controller.signal });
        clearTimeout(timeoutId);
        
        if (response.ok) {
            updateConnectionStatus(true);
            connectionRetryCount = 0;
            checkStreamStatus();
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
    connectionRetryCount++;
    if (connectionRetryCount <= MAX_RETRY_ATTEMPTS) {
        elements.connectionStatus.textContent = `Reconnecting (${connectionRetryCount})...`;
        const delay = Math.min(1000 * Math.pow(2, connectionRetryCount), 30000);
        setTimeout(checkConnection, delay);
    } else {
        elements.connectionStatus.textContent = 'Disconnected - Start backend';
    }
}

async function checkStreamStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/stream-status`);
        const data = await response.json();
        if (data.success && !data.running) startLiveStream();
        else if (data.success && data.running) streamStarted = true;
    } catch (error) {
        console.error('Error checking stream:', error);
    }
}

function updateConnectionStatus(connected) {
    if (!elements.connectionStatus || !elements.statusDot) return;
    
    if (connected) {
        elements.connectionStatus.textContent = 'Connected';
        elements.statusDot.classList.add('connected');
    } else {
        elements.connectionStatus.textContent = 'Disconnected';
        elements.statusDot.classList.remove('connected');
    }
}

async function loadCurrentUser() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/current-user`);
        const data = await response.json();
        
        if (data.success && data.logged_in) {
            currentUser.userId = data.user_id;
            currentUser.username = data.username;
            currentUser.email = data.email;
            currentUser.isVerified = data.is_verified;
            currentUser.mobileNumber = data.mobile_number;
            updateVerificationUI();
        }
        loadDashboardData();
    } catch (error) {
        console.error('Error loading user:', error);
        loadDashboardData();
    }
}

function updateVerificationUI() {
    if (!elements.verifiedBadge || !elements.btnVerify) return;
    
    if (currentUser.isVerified) {
        elements.verifiedBadge.style.display = 'inline-flex';
        elements.btnVerify.textContent = 'Update Mobile';
    } else {
        elements.verifiedBadge.style.display = 'none';
        elements.btnVerify.innerHTML = '<i class="fas fa-mobile-alt"></i> Verify Mobile';
    }
}

// OTP Functions
function showVerificationModal() {
    if (!elements.verificationModal) return;
    
    elements.verificationModal.style.display = 'block';
    showStep('step-phone');
    clearVerificationForm();
}

function closeVerificationModal() {
    if (!elements.verificationModal) return;
    
    elements.verificationModal.style.display = 'none';
    clearVerificationForm();
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
    
    if (otpTimerInterval) {
        clearInterval(otpTimerInterval);
        otpTimerInterval = null;
    }
    
    if (elements.otpTimer) elements.otpTimer.textContent = '';
    
    canResendOTP = true;
    otpExpiryTime = 0;
}

function showError(message) {
    if (!elements.verificationError) return;
    
    elements.verificationError.textContent = message;
    elements.verificationError.style.display = 'block';
}

async function sendOTP() {
    if (!canResendOTP && otpExpiryTime > Date.now()) {
        showError(`Please wait ${Math.ceil((otpExpiryTime - Date.now()) / 1000)} seconds before resending`);
        return;
    }
    
    const mobileNumber = elements.mobileNumberInput ? elements.mobileNumberInput.value.trim() : '';
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
            startOtpTimer(data.expires_in || 60);
            
            if (elements.otpTimer) {
                elements.otpTimer.innerHTML = `<span style="color: #10b981;">OTP sent! Expires in <span id="otp-countdown">${data.expires_in || 60}</span>s</span>`;
            }
            
            canResendOTP = false;
            otpExpiryTime = Date.now() + ((data.expires_in || 60) * 1000);
        } else {
            showError(data.error || 'Failed to send OTP');
        }
    } catch (error) {
        console.error('Error sending OTP:', error);
        showError('Failed to send OTP. Try again.');
    }
}

function startOtpTimer(seconds) {
    let remaining = seconds;
    
    if (otpTimerInterval) clearInterval(otpTimerInterval);
    
    otpTimerInterval = setInterval(() => {
        remaining--;
        
        const countdownEl = document.getElementById('otp-countdown');
        if (countdownEl) {
            countdownEl.textContent = remaining;
        }
        
        if (elements.otpTimer && remaining > 0) {
            elements.otpTimer.innerHTML = `<span style="color: #f59e0b;">Resend in ${remaining}s</span>`;
        }
        
        if (remaining <= 0) {
            clearInterval(otpTimerInterval);
            if (elements.otpTimer) {
                elements.otpTimer.innerHTML = `<span style="color: #ef4444;">OTP expired. Click resend.</span>`;
            }
            canResendOTP = true;
            otpExpiryTime = 0;
        }
    }, 1000);
}

async function verifyOTP() {
    const mobileNumber = elements.mobileNumberInput ? elements.mobileNumberInput.value.trim() : '';
    const otpCode = elements.otpCodeInput ? elements.otpCodeInput.value.trim() : '';
    
    if (!otpCode || otpCode.length !== 6) {
        showError('Please enter 6-digit OTP');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/verify-otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mobile_number: mobileNumber, otp_code: otpCode })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentUser.isVerified = true;
            currentUser.mobileNumber = data.mobile_number;
            updateVerificationUI();
            
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

// Stream functions
async function startLiveStream() {
    if (streamStarted) return;
    try {
        const response = await fetch(`${API_BASE_URL}/api/start-stream`, { method: 'POST' });
        const data = await response.json();
        if (data.success) streamStarted = true;
    } catch (error) {
        console.error('Error starting stream:', error);
    }
}

// Load Dashboard Data
async function loadDashboardData() {
    try {
        await Promise.all([loadStats(), loadTransactions(), loadAlerts()]);
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/stats`);
        const data = await response.json();
        
        if (data.success) {
            const stats = data.stats;
            
            if (elements.totalTransactions) elements.totalTransactions.textContent = stats.total_transactions.toLocaleString();
            if (elements.fraudTransactions) elements.fraudTransactions.textContent = stats.fraud_transactions.toLocaleString();
            if (elements.fraudPercentage) elements.fraudPercentage.textContent = `${stats.fraud_percentage}%`;
            if (elements.activeAlerts) elements.activeAlerts.textContent = stats.new_alerts;
            
            // Risk distribution
            const riskDist = stats.risk_distribution || {};
            const riskHigh = document.getElementById('risk-high');
            const riskMedium = document.getElementById('risk-medium');
            const riskLow = document.getElementById('risk-low');
            
            if (riskHigh) riskHigh.textContent = riskDist.HIGH || 0;
            if (riskMedium) riskMedium.textContent = riskDist.MEDIUM || 0;
            if (riskLow) riskLow.textContent = riskDist.LOW || 0;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

async function loadTransactions() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/transactions?limit=50`);
        const data = await response.json();
        
        if (data.success && data.transactions) {
            renderTransactions(data.transactions);
        } else {
            renderTransactions([]);
        }
    } catch (error) {
        console.error('Error loading transactions:', error);
    }
}

function renderTransactions(transactions) {
    if (!elements.transactionsBody) return;
    
    if (!transactions || transactions.length === 0) {
        elements.transactionsBody.innerHTML = '<tr class="loading"><td colspan="7">No transactions - Waiting for data...</td></tr>';
        return;
    }
    
    elements.transactionsBody.innerHTML = transactions.map(txn => `
        <tr class="${txn.is_fraud ? 'fraud-row' : ''}">
            <td><code>${(txn.transaction_id || '').substring(0, 12)}</code></td>
            <td class="amount">₹${(txn.amount || 0).toLocaleString()}</td>
            <td>${txn.transaction_type || 'N/A'}</td>
            <td>${txn.receiver_account || 'N/A'}</td>
            <td><span class="risk-badge ${(txn.risk_level || 'LOW').toLowerCase()}">${txn.risk_level || 'LOW'}</span></td>
            <td>${formatTime(txn.timestamp)}</td>
            <td>
                <span class="status-badge ${txn.is_fraud ? 'fraud' : 'normal'}">
                    ${txn.is_fraud ? '⚠️ Suspicious' : '✓ Normal'}
                </span>
            </td>
        </tr>
    `).join('');
}

async function loadAlerts() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/alerts?limit=20`);
        const data = await response.json();
        
        if (data.success) {
            renderAlerts(data.alerts || []);
            if (elements.alertCount) elements.alertCount.textContent = data.count || 0;
        }
    } catch (error) {
        console.error('Error loading alerts:', error);
    }
}

function renderAlerts(alerts) {
    if (!elements.alertsContainer) return;
    
    if (!alerts || alerts.length === 0) {
        elements.alertsContainer.innerHTML = '<div class="no-alerts">No fraud alerts detected</div>';
        return;
    }
    
    elements.alertsContainer.innerHTML = alerts.map(alert => `
        <div class="alert-card ${(alert.risk_level || 'HIGH').toLowerCase()}">
            <div class="alert-header">
                <h4>🚨 ${alert.alert_type || 'Fraud Alert'}</h4>
                <span class="risk-badge ${(alert.risk_level || 'HIGH').toLowerCase()}">${alert.risk_level || 'HIGH'}</span>
            </div>
            <p><strong>Transaction:</strong> ${alert.transaction_id}</p>
            <p><strong>Amount:</strong> ₹${(alert.amount || 0).toLocaleString()}</p>
            <p>${alert.alert_message || ''}</p>
            <div class="alert-footer">
                <span class="alert-time">${formatTime(alert.alert_time)}</span>
                <span class="alert-status">${alert.status || 'new'}</span>
            </div>
        </div>
    `).join('');
}

function refreshTransactions() {
    loadDashboardData();
}

function setupAutoRefresh() {
    if (elements.autoRefreshToggle) {
        elements.autoRefreshToggle.addEventListener('change', (e) => {
            autoRefreshEnabled = e.target.checked;
        });
    }
    
    setInterval(() => {
        if (autoRefreshEnabled) loadDashboardData();
    }, refreshInterval);
}

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

// Close modal on outside click
window.onclick = function(event) {
    if (elements.verificationModal && event.target === elements.verificationModal) {
        closeVerificationModal();
    }
};

// Error handling
window.addEventListener('error', (e) => {
    console.error('Global error:', e.error);
});

// Make API_BASE_URL available globally for charts.js
window.API_BASE_URL = API_BASE_URL;

