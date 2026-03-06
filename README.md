# 🛡️ Real-Time Fraud Detection System

A comprehensive real-time fraud detection system for bank transactions built with Python, Flask, Machine Learning, and includes OTP Verification, SMS/Email Alerts, and Call Fraud Detection.

## 📋 Project Overview

This project demonstrates a complete fraud detection pipeline:
- **Transaction Generator** - Simulates real bank transactions
- **ML Model** - Rule-based + ML hybrid for fraud detection
- **Backend API** - Flask REST API with all features
- **Frontend Dashboard** - Real-time monitoring with auto-reconnect

## 🎯 Features

### Backend
- ✅ RESTful API with Flask
- ✅ Machine Learning model for fraud detection (Rule-based + ML hybrid)
- ✅ Real-time transaction processing
- ✅ Fraud probability scoring
- ✅ Transaction history and alerts
- ✅ Auto-start live transaction stream
- ✅ **OTP Verification System** - Verify mobile number before calls
- ✅ **SMS Alerts** - Simulated SMS for fraud alerts
- ✅ **Email Alerts** - SMTP email notifications for suspicious activity
- ✅ **Call Fraud Detection** - Detect suspicious calling patterns
- ✅ **Admin Dashboard** - View all suspicious activities

### Frontend
- ✅ Modern dark-themed dashboard
- ✅ Live transaction feed (auto-refreshes every 3 seconds)
- ✅ Fraud alerts panel with notifications
- ✅ Real-time statistics
- ✅ **Auto-reconnect** - Automatically reconnects when backend restarts
- ✅ **Auto-start stream** - Automatically starts transaction stream

## 🚀 Quick Start

### Step 1: Install Dependencies

```
bash
cd c:\Users\Pooja\Desktop\project
pip install -r requirements.txt
```

### Step 2: Run the Application

**Option A: Using the startup script (Windows)**
```bash
start_backend.bat
```

**Option B: Using Python directly**
```bash
python main.py
```

### Step 3: Open the Dashboard

**Recommended: Use a local server**
```
bash
cd frontend_dashboard
python -m http.server 8080
```

Then open: http://localhost:8080/index.html

## 📊 API Endpoints

### Standard Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/api/` | GET | API information |
| `/api/health` | GET | Health status |
| `/api/transactions` | GET | Get transactions |
| `/api/recent-transactions` | GET | Recent transactions |
| `/api/alerts` | GET | Fraud alerts |
| `/api/stats` | GET | Statistics |
| `/api/start-stream` | POST | Start stream |
| `/api/stop-stream` | POST | Stop stream |

### OTP Verification
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/send-otp` | POST | Send OTP |
| `/api/verify-otp` | POST | Verify OTP |
| `/api/verification-status` | GET | Verification status |

### Call Fraud Detection
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/attempt-call` | POST | Attempt call with OTP |
| `/api/verify-call-otp` | POST | Verify call OTP |
| `/api/suspicious-activities` | GET | Suspicious activities |

### Admin
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/admin/stats` | GET | Admin stats |
| `/api/admin/all-activities` | GET | All activities |

## 🔐 OTP Verification System

When a user attempts to dial another number:
1. System sends OTP to user's registered mobile number
2. User must verify OTP before call is allowed
3. Verified users are stored in the database

## 🚨 Fraud / Suspicious Activity Alert

The system detects suspicious behavior:
- Repeated calls to unknown numbers (5+ times in an hour)
- Unusual calling patterns (calling many different numbers)
- High amount transactions ($5000+)

Alert Actions:
- ✅ Send SMS alert to user
- ✅ Send email notification to admin

## 👨‍💼 Admin Dashboard

Shows all suspicious activities:
- User number
- Suspicious action
- Time of activity
- Alert status

## 🛠️ Troubleshooting

### Dashboard shows "Disconnected"
1. Make sure backend is running: `python main.py`
2. The dashboard will automatically reconnect
3. If not, refresh the browser page

### Port 5000 already in use
```
bash
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

## 📝 License

This project is for educational purposes.
