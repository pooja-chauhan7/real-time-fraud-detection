/**
 * SecureBank Fraud Detection Dashboard
 * Real-time transaction monitoring with fraud detection
 */

const API_BASE_URL = 'http://localhost:5000';

// State management
let autoRefreshEnabled = true;
let refreshInterval = 4000; // 4 seconds
let streamStarted = false;
let connectionRetryCount = 0;
const MAX_RETRY_ATTEMPTS = 10;
let chartsInitialized = false;
let mapInitialized = false;
let lastTransactionCount = 0;
let lastAlertCount = 0;
let map = null;
let markers = [];

// DOM Elements
const elements = {
    connectionDot: document.getElementById('connection-dot'),
    connectionText: document.getElementById('connection-text'),
    apiStatus: document.getElementById('api-status'),
    streamStatus: document.getElementById('stream-status'),
    dbStatus: document.getElementById('db-status'),
    totalTransactions: document.getElementById('total-transactions'),
    normalTransactions: document.getElementById('normal-transactions'),
    fraudTransactions: document.getElementById('fraud-transactions'),
    activeAlerts: document.getElementById('active-alerts'),
    highRiskCount: document.getElementById('high-risk-count'),
    riskHigh: document.getElementById('risk-high'),
    riskMedium: document.getElementById('risk-medium'),
    riskLow: document.getElementById('risk-low'),
    transactionsBody: document.getElementById('transactions-body'),
    alertsContainer: document.getElementById('alerts-container'),
    alertBadge: document.getElementById('alert-badge'),
    suspiciousList: document.getElementById('suspicious-list'),
    locationCount: document.getElementById('location-count'),
    verificationModal: document.getElementById('verification-modal'),
    fraudAlertPopup: document.getElementById('fraud-alert-popup')
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('SecureBank Fraud Dashboard initializing...');
    initUpload();
    initAnalyzeForm();
    initCharts();
    initMap();
    checkConnection();
    setupAutoRefresh();
    startLiveUpdates();
});

// Check connection status
async function checkConnection() {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);

        const response = await fetch(`${API_BASE_URL}/api/`, { signal: controller.signal });
        clearTimeout(timeoutId);

        if (response.ok) {
            updateConnectionStatus(true);
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
        const delay = Math.min(1000 * Math.pow(2, Math.min(connectionRetryCount, 5)), 30000);
        setTimeout(checkConnection, delay);
    }
}

function updateConnectionStatus(connected) {
    if (elements.connectionDot && elements.connectionText) {
        if (connected) {
            elements.connectionDot.classList.add('connected');
            elements.connectionText.textContent = 'Connected';
        } else {
            elements.connectionDot.classList.remove('connected');
            elements.connectionText.textContent = 'Disconnected';
        }
    }
    if (elements.apiStatus) {
        elements.apiStatus.classList.toggle('connected', connected);
    }
    if (elements.dbStatus) {
        elements.dbStatus.classList.toggle('connected', connected);
    }
}

// Check stream status
async function checkStreamStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/stream-status`);
        const data = await response.json();
        
        if (data.success) {
            streamStarted = data.running;
            if (elements.streamStatus) {
                elements.streamStatus.classList.toggle('connected', streamStarted);
            }
        }
    } catch (error) {
        console.error('Error checking stream status:', error);
    }
}

// Initialize Map
function initMap() {
    if (mapInitialized) return;
    
    const mapContainer = document.getElementById('transaction-map');
    if (!mapContainer) return;
    
    try {
        map = L.map('transaction-map').setView([20, 0], 2);
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);
        
        mapInitialized = true;
        console.log('Map initialized');
    } catch (error) {
        console.error('Error initializing map:', error);
    }
}

// Add marker to map
function addTransactionMarker(location, isFraud) {
    if (!mapInitialized || !map) return;
    
    // Location coordinates (simulated)
    const coords = getLocationCoords(location);
    if (!coords) return;
    
    const color = isFraud ? 'red' : 'green';
    
    const icon = L.divIcon({
        className: 'custom-marker',
        html: `<div style="background-color: ${color}; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
        iconSize: [12, 12],
        iconAnchor: [6, 6]
    });
    
    const marker = L.marker([coords.lat, coords.lng], { icon }).addTo(map);
    marker.bindPopup(`<b>${location}</b><br>${isFraud ? '⚠️ Fraud' : '✓ Normal'}`);
    
    markers.push(marker);
    
    // Update count
    if (elements.locationCount) {
        elements.locationCount.textContent = markers.length;
    }
}

// Get coordinates for location
function getLocationCoords(location) {
    const locationCoords = {
        'New York, USA': { lat: 40.7128, lng: -74.0060 },
        'Los Angeles, USA': { lat: 34.0522, lng: -118.2437 },
        'Chicago, USA': { lat: 41.8781, lng: -87.6298 },
        'Houston, USA': { lat: 29.7604, lng: -95.3698 },
        'Phoenix, USA': { lat: 33.4484, lng: -112.0740 },
        'London, UK': { lat: 51.5074, lng: -0.1278 },
        'Paris, France': { lat: 48.8566, lng: 2.3522 },
        'Berlin, Germany': { lat: 52.5200, lng: 13.4050 },
        'Tokyo, Japan': { lat: 35.6762, lng: 139.6503 },
        'Sydney, Australia': { lat: -33.8688, lng: 151.2093 },
        'Toronto, Canada': { lat: 43.6532, lng: -79.3832 },
        'Mumbai, India': { lat: 19.0760, lng: 72.8777 },
        'Dubai, UAE': { lat: 25.2048, lng: 55.2708 },
        'Singapore': { lat: 1.3521, lng: 103.8198 },
        'Hong Kong': { lat: 22.3193, lng: 114.1694 },
        'Seoul, South Korea': { lat: 37.5665, lng: 126.9780 },
        'Unknown Location': { lat: 0, lng: 0 },
        'Test Location': { lat: 0, lng: 0 },
        'Offshore': { lat: 0, lng: 0 }
    };
    
    return locationCoords[location] || null;
}

// Initialize Charts
function initCharts() {
    const checkChart = setInterval(() => {
        if (typeof Chart !== 'undefined') {
            clearInterval(checkChart);
            initializeCharts();
        }
    }, 100);
    
    setTimeout(() => clearInterval(checkChart), 5000);
}

function initializeCharts() {
    if (chartsInitialized) return;
    
    // Pie Chart - Fraud vs Normal
    const pieCtx = document.getElementById('fraud-pie-chart');
    if (pieCtx) {
        window.fraudPieChart = new Chart(pieCtx, {
            type: 'doughnut',
            data: {
                labels: ['Normal', 'Fraud'],
                datasets: [{
                    data: [80, 20],
                    backgroundColor: ['#10b981', '#ef4444'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { 
                    legend: { position: 'bottom', labels: { color: '#94a3b8' } }
                },
                cutout: '70%'
            }
        });
    }
    
    // Line Chart - Transaction Volume
    const lineCtx = document.getElementById('volume-line-chart');
    if (lineCtx) {
        const hours = Array.from({length: 12}, (_, i) => {
            const d = new Date();
            d.setHours(d.getHours() - (11 - i));
            return d.getHours() + ':00';
        });
        
        window.volumeLineChart = new Chart(lineCtx, {
            type: 'line',
            data: {
                labels: hours,
                datasets: [
                    {
                        label: 'Normal',
                        data: Array.from({length: 12}, () => Math.floor(Math.random() * 30) + 10),
                        borderColor: '#10b981',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Fraud',
                        data: Array.from({length: 12}, () => Math.floor(Math.random() * 5) + 1),
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
                plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8' } } },
                scales: { 
                    y: { beginAtZero: true, grid: { color: 'rgba(148, 163, 184, 0.1)' }, ticks: { color: '#94a3b8' } },
                    x: { grid: { color: 'rgba(148, 163, 184, 0.1)' }, ticks: { color: '#94a3b8' } }
                }
            }
        });
    }
    
    // Bar Chart - Risk Distribution
    const barCtx = document.getElementById('risk-bar-chart');
    if (barCtx) {
        window.riskBarChart = new Chart(barCtx, {
            type: 'bar',
            data: {
                labels: ['Low', 'Medium', 'High'],
                datasets: [{
                    label: 'Transactions',
                    data: [50, 30, 20],
                    backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
                    borderRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { 
                    y: { beginAtZero: true, grid: { color: 'rgba(148, 163, 184, 0.1)' }, ticks: { color: '#94a3b8' } },
                    x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
                }
            }
        });
    }
    
    // Timeline Chart
    const timelineCtx = document.getElementById('timeline-chart');
    if (timelineCtx) {
        window.timelineChart = new Chart(timelineCtx, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'Fraud Detections',
                    data: [3, 5, 2, 8, 4, 6, 3],
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.2)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { 
                    y: { beginAtZero: true, grid: { color: 'rgba(148, 163, 184, 0.1)' }, ticks: { color: '#94a3b8' } },
                    x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
                }
            }
        });
    }
    
    chartsInitialized = true;
    console.log('Charts initialized');
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
        if (e.dataTransfer.files.length > 0) uploadFile(e.dataTransfer.files[0]);
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
            loadDashboardData();
        } else {
            alert(data.error || 'Upload failed');
            initUpload();
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
    
    if (document.getElementById('result-total')) {
        document.getElementById('result-total').textContent = results.total_transactions;
    }
    if (document.getElementById('result-amount')) {
        document.getElementById('result-amount').textContent = `₹${results.total_amount.toLocaleString()}`;
    }
    if (document.getElementById('result-suspicious')) {
        document.getElementById('result-suspicious').textContent = results.suspicious_transactions;
    }
    
    // Reset upload area
    const uploadArea = document.getElementById('upload-area');
    if (uploadArea) {
        uploadArea.innerHTML = `
            <i class="fas fa-cloud-upload-alt"></i>
            <h3>Drop your CSV file here</h3>
            <p>or click to browse</p>
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
        const location = document.getElementById('analyze-location').value;
        
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
                    location: location || 'Online'
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                displayAnalysisResult(data.analysis);
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

function displayAnalysisResult(analysis) {
    const resultDiv = document.getElementById('analysis-result');
    const contentDiv = document.getElementById('analysis-content');
    
    if (!resultDiv || !contentDiv) return;
    
    resultDiv.style.display = 'block';
    
    const riskClass = analysis.risk_level.toLowerCase();
    const riskColor = analysis.is_fraud ? '#ef4444' : analysis.risk_level === 'MEDIUM' ? '#f59e0b' : '#10b981';
    const riskIcon = analysis.is_fraud ? 'fa-exclamation-triangle' : 'fa-check-circle';
    
    const riskScore = Math.round(analysis.risk_score || analysis.fraud_probability * 100);
    
    contentDiv.innerHTML = `
        <div class="risk-score ${riskClass}" style="color: ${riskColor}">${riskScore}</div>
        <div class="risk-label" style="color: ${riskColor}">${analysis.risk_level} RISK</div>
        <div class="details">
            <p><strong>Fraud Detected:</strong> ${analysis.is_fraud ? '⚠️ Yes' : '✓ No'}</p>
            <p><strong>Fraud Probability:</strong> ${(analysis.fraud_probability * 100).toFixed(1)}%</p>
            ${analysis.fraud_reason ? `<p><strong>Reason:</strong> ${analysis.fraud_reason}</p>` : ''}
        </div>
    `;
}

// Auto refresh
function setupAutoRefresh() {
    const autoRefreshToggle = document.getElementById('auto-refresh');
    if (autoRefreshToggle) {
        autoRefreshToggle.addEventListener('change', (e) => {
            autoRefreshEnabled = e.target.checked;
        });
    }
}

// Live updates
let liveUpdateInterval = null;

function startLiveUpdates() {
    if (liveUpdateInterval) return;
    
    liveUpdateInterval = setInterval(() => {
        if (autoRefreshEnabled) {
            checkForNewData();
        }
    }, refreshInterval);
}

async function checkForNewData() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/stats`);
        const data = await response.json();
        
        if (data.success) {
            const stats = data.stats;
            
            // Only update if there are changes
            if (stats.total_transactions !== lastTransactionCount || stats.new_alerts !== lastAlertCount) {
                lastTransactionCount = stats.total_transactions;
                lastAlertCount = stats.new_alerts;
                loadDashboardData();
                updateCharts(stats);
            }
        }
    } catch (error) {
        console.error('Error checking for new data:', error);
    }
}

function updateCharts(stats) {
    if (window.fraudPieChart) {
        window.fraudPieChart.data.datasets[0].data = [
            stats.normal_transactions || 0,
            stats.fraud_transactions || 0
        ];
        window.fraudPieChart.update('none');
    }
    
    if (window.riskBarChart && stats.risk_distribution) {
        window.riskBarChart.data.datasets[0].data = [
            stats.risk_distribution.LOW || 0,
            stats.risk_distribution.MEDIUM || 0,
            stats.risk_distribution.HIGH || 0
        ];
        window.riskBarChart.update('none');
    }
}

// Load Dashboard Data
async function loadDashboardData() {
    try {
        await Promise.all([loadStats(), loadTransactions(), loadAlerts(), loadSuspiciousAccounts()]);
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
            if (elements.normalTransactions) elements.normalTransactions.textContent = stats.normal_transactions.toLocaleString();
            if (elements.fraudTransactions) elements.fraudTransactions.textContent = stats.fraud_transactions.toLocaleString();
            if (elements.activeAlerts) elements.activeAlerts.textContent = stats.new_alerts;
            if (elements.highRiskCount) elements.highRiskCount.textContent = stats.high_risk_transactions || 0;
            
            const riskDist = stats.risk_distribution || {};
            if (elements.riskHigh) elements.riskHigh.textContent = riskDist.HIGH || 0;
            if (elements.riskMedium) elements.riskMedium.textContent = riskDist.MEDIUM || 0;
            if (elements.riskLow) elements.riskLow.textContent = riskDist.LOW || 0;
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
            
            // Add markers for recent transactions
            if (mapInitialized) {
                data.transactions.slice(0, 10).forEach(txn => {
                    addTransactionMarker(txn.location, txn.is_fraud);
                });
            }
        }
    } catch (error) {
        console.error('Error loading transactions:', error);
    }
}

function renderTransactions(transactions) {
    if (!elements.transactionsBody) return;
    
    if (!transactions || transactions.length === 0) {
        elements.transactionsBody.innerHTML = '<tr><td colspan="8" class="loading-cell">No transactions - Waiting for data...</td></tr>';
        return;
    }
    
    elements.transactionsBody.innerHTML = transactions.map(txn => {
        const riskScore = Math.round((txn.fraud_probability || 0) * 100);
        const riskClass = riskScore >= 71 ? 'high' : riskScore >= 31 ? 'medium' : 'low';
        
        return `
            <tr class="${txn.is_fraud ? 'fraud-row' : ''}">
                <td><code>${(txn.transaction_id || '').substring(0, 15)}</code></td>
                <td>${txn.user_id || 'N/A'}</td>
                <td class="amount">₹${(txn.amount || 0).toLocaleString()}</td>
                <td>${txn.transaction_type || 'TRANSFER'}</td>
                <td>${txn.location || 'N/A'}</td>
                <td><span class="risk-badge ${riskClass}">${riskScore}</span></td>
                <td><span class="status-badge ${txn.is_fraud ? 'fraud' : 'normal'}">${txn.is_fraud ? '⚠️ Fraud' : '✓ Normal'}</span></td>
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
            if (elements.alertBadge) elements.alertBadge.textContent = data.count || 0;
            
            // Check for new alerts and show popup
            if (data.alerts && data.alerts.length > 0) {
                const newestAlert = data.alerts[0];
                if (newestAlert.status === 'new') {
                    showFraudAlert(newestAlert);
                }
            }
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
            <h4>🚨 ${alert.alert_type || 'Fraud Alert'}</h4>
            <p><strong>Transaction:</strong> ${alert.transaction_id}</p>
            <p><strong>Amount:</strong> ₹${(alert.amount || 0).toLocaleString()}</p>
            <p>${alert.alert_message || ''}</p>
            <div class="alert-footer">
                <span>${formatTime(alert.alert_time)}</span>
                <span>${alert.status || 'new'}</span>
            </div>
        </div>
    `).join('');
}

async function loadSuspiciousAccounts() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/analytics`);
        const data = await response.json();
        
        if (data.success && data.analytics && data.analytics.suspicious_accounts) {
            renderSuspiciousAccounts(data.analytics.suspicious_accounts);
        }
    } catch (error) {
        console.error('Error loading suspicious accounts:', error);
    }
}

function renderSuspiciousAccounts(accounts) {
    if (!elements.suspiciousList) return;
    
    if (!accounts || accounts.length === 0) {
        elements.suspiciousList.innerHTML = '<div class="no-data">No suspicious accounts detected</div>';
        return;
    }
    
    elements.suspiciousList.innerHTML = accounts.slice(0, 5).map(account => `
        <div class="suspicious-item">
            <div class="suspicious-info">
                <h4>${account.user_id}</h4>
                <p>${account.total_transactions} transactions</p>
            </div>
            <div class="suspicious-score">
                <div class="score">${account.fraud_count}</div>
                <div class="label">fraud cases</div>
            </div>
        </div>
    `).join('');
}

// Show Fraud Alert Popup
function showFraudAlert(alert) {
    const popup = elements.fraudAlertPopup;
    if (!popup || popup.classList.contains('hidden')) {
        // Show popup
        if (popup) {
            popup.classList.remove('hidden');
            
            document.getElementById('popup-txn-id').textContent = alert.transaction_id;
            document.getElementById('popup-amount').textContent = `₹${(alert.amount || 0).toLocaleString()}`;
            document.getElementById('popup-location').textContent = alert.location || 'Unknown';
            
            const riskEl = document.getElementById('popup-risk');
            riskEl.textContent = alert.risk_level || 'HIGH';
            riskEl.className = `popup-value risk-badge ${(alert.risk_level || 'HIGH').toLowerCase()}`;
            
            document.getElementById('popup-reason').textContent = alert.alert_message || 'Suspicious transaction detected';
            
            // Play alert sound
            playAlertSound();
            
            // Auto close after 10 seconds
            setTimeout(() => {
                closeFraudPopup();
            }, 10000);
        }
    }
}

function closeFraudPopup() {
    const popup = elements.fraudAlertPopup;
    if (popup) {
        popup.classList.add('hidden');
    }
}

function playAlertSound() {
    try {
        const audio = document.getElementById('fraud-alert-sound');
        if (audio) {
            audio.volume = 0.5;
            audio.play().catch(e => console.log('Audio play failed:', e));
        }
    } catch (e) {
        console.log('Audio not available');
    }
}

// Demo Functions
async function generateDemoTransactions() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/generate-demo`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ count: 10 })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`Generated ${data.generated} demo transactions (${data.fraud_detected} flagged as fraud)`);
            loadDashboardData();
        }
    } catch (error) {
        console.error('Error generating demo:', error);
        alert('Failed to generate demo. Make sure backend is running.');
    }
}

async function startStream() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/start-stream`, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            streamStarted = true;
            if (elements.streamStatus) {
                elements.streamStatus.classList.add('connected');
            }
            alert('Transaction stream started!');
        }
    } catch (error) {
        console.error('Error starting stream:', error);
        alert('Failed to start stream. Make sure backend is running.');
    }
}

async function stopStream() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/stop-stream`, { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            streamStarted = false;
            if (elements.streamStatus) {
                elements.streamStatus.classList.remove('connected');
            }
            alert('Transaction stream stopped!');
        }
    } catch (error) {
        console.error('Error stopping stream:', error);
    }
}

async function downloadReport() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/download-report`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `fraud_report_${new Date().toISOString().slice(0,10)}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            alert('Failed to download report');
        }
    } catch (error) {
        console.error('Error downloading report:', error);
        alert('Failed to download report. Make sure backend is running.');
    }
}

function refreshData() {
    loadDashboardData();
}

// Utility Functions
function formatTime(timestamp) {
    if (!timestamp) return 'N/A';
    try {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff/60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff/3600000)}h ago`;
        return date.toLocaleDateString();
    } catch (e) {
        return timestamp;
    }
}

// Modal functions
function showVerificationModal() {
    if (elements.verificationModal) {
        elements.verificationModal.style.display = 'flex';
    }
}

function closeModal() {
    if (elements.verificationModal) {
        elements.verificationModal.style.display = 'none';
    }
}

async function sendOTP() {
    const mobileNumber = document.getElementById('mobile-number')?.value.trim();
    if (!mobileNumber) {
        showVerificationError('Please enter mobile number');
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
            document.getElementById('step-phone').style.display = 'none';
            document.getElementById('step-otp').style.display = 'block';
        } else {
            showVerificationError(data.error || 'Failed to send OTP');
        }
    } catch (error) {
        showVerificationError('Failed to send OTP');
    }
}

async function verifyOTP() {
    const mobileNumber = document.getElementById('mobile-number')?.value.trim();
    const otpCode = document.getElementById('otp-code')?.value.trim();
    
    if (!otpCode || otpCode.length !== 6) {
        showVerificationError('Please enter 6-digit OTP');
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
            document.getElementById('step-otp').style.display = 'none';
            document.getElementById('step-verified').style.display = 'block';
        } else {
            showVerificationError(data.error || 'Invalid OTP');
        }
    } catch (error) {
        showVerificationError('Verification failed');
    }
}

function showVerificationError(message) {
    const errorEl = document.getElementById('verification-error');
    if (errorEl) {
        errorEl.textContent = message;
        errorEl.style.display = 'block';
    }
}

// Close modal on outside click
window.onclick = function(event) {
    if (elements.verificationModal && event.target === elements.verificationModal) {
        closeModal();
    }
};

// Make functions available globally
window.generateDemoTransactions = generateDemoTransactions;
window.startStream = startStream;
window.stopStream = stopStream;
window.downloadReport = downloadReport;
window.refreshData = refreshData;
window.closeFraudPopup = closeFraudPopup;
window.showVerificationModal = showVerificationModal;
window.closeModal = closeModal;
window.sendOTP = sendOTP;
window.verifyOTP = verifyOTP;
window.API_BASE_URL = API_BASE_URL;

