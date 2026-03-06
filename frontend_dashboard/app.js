// Fraud Detection Dashboard - JavaScript
// With OTP Verification and User-Specific Alerts

const API_BASE_URL = 'http://localhost:5000';
let autoRefreshEnabled = true;
let refreshInterval = 3000; // 3 seconds
let streamStarted = false;
let connectionRetryCount = 0;
const MAX_RETRY_ATTEMPTS = 10;
let connectionCheckInterval = null;

// User state
let currentUser = {
    userId: null,
    username: null,
    isVerified: false,
    mobileNumber: null
};

// OTP state
let otpExpiryTime = null;
let otpTimerInterval = null;

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
    // Verification elements
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

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard initializing...');
    checkConnection();
    loadCurrentUser();
    setupAutoRefresh();
    startLiveStream();
    
    // Set up periodic connection check every 10 seconds
    connectionCheckInterval = setInterval(checkConnection, 10000);
});

// Check API connection with auto-reconnect
async function checkConnection() {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        const response = await fetch(`${API_BASE_URL}/api/`, {
            method: 'GET',
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
            updateConnectionStatus(true);
            connectionRetryCount = 0;
            const data = await response.json();
            console.log('API Connected:', data);
            
            // If stream is not started, auto-start it
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

// Handle disconnection with auto-reconnect
function handleDisconnection() {
    connectionRetryCount++;
    
    if (connectionRetryCount <= MAX_RETRY_ATTEMPTS) {
        console.log(`Connection lost. Retry attempt ${connectionRetryCount}/${MAX_RETRY_ATTEMPTS}`);
        
        // Show reconnecting status
        elements.connectionStatus.textContent = `Reconnecting (${connectionRetryCount})...`;
        
        // Try to reconnect after delay (exponential backoff)
        const delay = Math.min(1000 * Math.pow(2, connectionRetryCount), 30000);
        setTimeout(checkConnection, delay);
    } else {
        elements.connectionStatus.textContent = 'Disconnected - Please start backend server';
        console.error('Max reconnection attempts reached. Please start the backend server.');
    }
}

// Check stream status and auto-start if not running
async function checkStreamStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/stream-status`);
        const data = await response.json();
        
        if (data.success && !data.running) {
            console.log('Stream not running. Auto-starting...');
            startLiveStream();
        } else if (data.success && data.running) {
            streamStarted = true;
            console.log('Stream already running');
        }
    } catch (error) {
        console.error('Error checking stream status:', error);
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

// Load current user
async function loadCurrentUser() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/current-user`);
        const data = await response.json();
        
        if (data.success && data.logged_in) {
            currentUser.userId = data.user_id;
            currentUser.username = data.username;
            currentUser.isVerified = data.is_verified;
            currentUser.mobileNumber = data.mobile_number;
            
            updateVerificationUI();
            loadDashboardData();
        } else {
            // Not logged in - still load general data
            loadDashboardData();
        }
    } catch (error) {
        console.error('Error loading user:', error);
        loadDashboardData();
    }
}

function updateVerificationUI() {
    if (currentUser.isVerified) {
        elements.verifiedBadge.style.display = 'inline-block';
        elements.btnVerify.textContent = 'Update Mobile';
        elements.btnVerify.onclick = showVerificationModal;
    } else {
        elements.verifiedBadge.style.display = 'none';
        elements.btnVerify.textContent = '🔐 Verify Mobile';
        elements.btnVerify.onclick = showVerificationModal;
    }
}

// Modal functions
function showVerificationModal() {
    elements.verificationModal.style.display = 'block';
    showStep('step-phone');
    clearVerificationForm();
}

function closeVerificationModal() {
    elements.verificationModal.style.display = 'none';
    clearVerificationForm();
}

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target === elements.verificationModal) {
        closeVerificationModal();
    }
};

function showStep(stepId) {
    elements.stepPhone.style.display = 'none';
    elements.stepOtp.style.display = 'none';
    elements.stepVerified.style.display = 'none';
    elements.verificationError.style.display = 'none';
    
    document.getElementById(stepId).style.display = 'block';
}

function clearVerificationForm() {
    elements.mobileNumberInput.value = '';
    elements.otpCodeInput.value = '';
    elements.verificationError.style.display = 'none';
    if (otpTimerInterval) {
        clearInterval(otpTimerInterval);
        otpTimerInterval = null;
    }
    elements.otpTimer.textContent = '';
}

function showError(message) {
    elements.verificationError.textContent = message;
    elements.verificationError.style.display = 'block';
}

// OTP Functions
async function sendOTP() {
    const mobileNumber = elements.mobileNumberInput.value.trim();
    
    if (!mobileNumber) {
        showError('Please enter your mobile number');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/send-otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                mobile_number: mobileNumber,
                user_id: currentUser.userId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showStep('step-otp');
            startOtpTimer(data.expires_in);
            elements.otpTimer.textContent = `OTP sent! Expires in ${data.expires_in / 60} minutes.`;
        } else {
            showError(data.error || 'Failed to send OTP');
        }
    } catch (error) {
        console.error('Error sending OTP:', error);
        showError('Failed to send OTP. Please try again.');
    }
}

function startOtpTimer(seconds) {
    let remaining = seconds;
    
    if (otpTimerInterval) {
        clearInterval(otpTimerInterval);
    }
    
    otpTimerInterval = setInterval(() => {
        remaining--;
        const mins = Math.floor(remaining / 60);
        const secs = remaining % 60;
        elements.otpTimer.textContent = `Resend available in ${mins}:${secs.toString().padStart(2, '0')}`;
        
        if (remaining <= 0) {
            clearInterval(otpTimerInterval);
            elements.otpTimer.textContent = 'OTP expired. Please resend.';
        }
    }, 1000);
}

async function verifyOTP() {
    const mobileNumber = elements.mobileNumberInput.value.trim();
    const otpCode = elements.otpCodeInput.value.trim();
    
    if (!otpCode) {
        showError('Please enter the OTP code');
        return;
    }
    
    if (otpCode.length !== 6) {
        showError('OTP must be 6 digits');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/verify-otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                mobile_number: mobileNumber,
                otp_code: otpCode,
                user_id: currentUser.userId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentUser.isVerified = true;
            currentUser.mobileNumber = data.mobile_number;
            
            updateVerificationUI();
            
            // Show verified step
            elements.verifiedNumber.textContent = `Verified: ${data.mobile_number}`;
            showStep('step-verified');
            
            // Reload dashboard to get user-specific data
            loadDashboardData();
        } else {
            showError(data.error || 'Invalid OTP');
        }
    } catch (error) {
        console.error('Error verifying OTP:', error);
        showError('Failed to verify OTP. Please try again.');
    }
}

// Start live transaction stream
async function startLiveStream() {
    if (streamStarted) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/start-stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (data.success) {
            streamStarted = true;
            console.log('Live stream started');
        }
    } catch (error) {
        console.error('Error starting stream:', error);
    }
}

// Stop live transaction stream
async function stopLiveStream() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/stop-stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        
        if (data.success) {
            streamStarted = false;
            console.log('Live stream stopped');
        }
    } catch (error) {
        console.error('Error stopping stream:', error);
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
        const url = currentUser.userId 
            ? `${API_BASE_URL}/api/stats?user_id=${currentUser.userId}`
            : `${API_BASE_URL}/api/stats`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            const stats = data.stats;
            elements.totalTransactions.textContent = formatNumber(stats.total_transactions);
            elements.fraudTransactions.textContent = formatNumber(stats.fraud_transactions);
            elements.fraudPercentage.textContent = `${stats.fraud_percentage}%`;
            elements.activeAlerts.textContent = stats.new_alerts || 0;
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// Load recent transactions
async function loadTransactions() {
    try {
        const url = currentUser.userId 
            ? `${API_BASE_URL}/api/recent-transactions?limit=20&user_id=${currentUser.userId}`
            : `${API_BASE_URL}/api/recent-transactions?limit=20`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success && data.transactions) {
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
    if (!transactions || transactions.length === 0) {
        elements.transactionsBody.innerHTML = `
            <tr class="loading">
                <td colspan="6">No transactions yet - Waiting for stream...</td>
            </tr>
        `;
        return;
    }
    
    const html = transactions.map(txn => `
        <tr class="${txn.is_fraud ? 'fraud-row' : ''}">
            <td><code>${txn.transaction_id || 'N/A'}</code></td>
            <td>${txn.user_id || 'N/A'}</td>
            <td class="amount">$${formatNumber(txn.amount || 0)}</td>
            <td>${txn.location || txn.merchant || 'N/A'}</td>
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
        const url = currentUser.userId 
            ? `${API_BASE_URL}/api/alerts?user_id=${currentUser.userId}`
            : `${API_BASE_URL}/api/alerts`;
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            renderAlerts(data.alerts || []);
            elements.alertCount.textContent = data.count || 0;
        }
    } catch (error) {
        console.error('Error loading alerts:', error);
    }
}

// Render alerts
function renderAlerts(alerts) {
    if (!alerts || alerts.length === 0) {
        elements.alertsContainer.innerHTML = `
            <div class="no-alerts">No fraud alerts detected</div>
        `;
        return;
    }
    
    const html = alerts.map(alert => `
        <div class="alert-card">
            <h4>🚨 Fraud Detected</h4>
            <p><strong>Transaction:</strong> ${alert.transaction_id}</p>
            <p><strong>User:</strong> ${alert.user_id || 'N/A'}</p>
            <p><strong>Amount:</strong> $${formatNumber(alert.amount)}</p>
            <p><strong>Risk:</strong> ${alert.risk_level || 'HIGH'}</p>
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
    if (elements.autoRefreshToggle) {
        elements.autoRefreshToggle.addEventListener('change', (e) => {
            autoRefreshEnabled = e.target.checked;
        });
    }
    
    // Set up interval
    setInterval(() => {
        if (autoRefreshEnabled) {
            loadDashboardData();
        }
    }, refreshInterval);
}

// Format number with commas
function formatNumber(num) {
    if (num === undefined || num === null) return '0.00';
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

