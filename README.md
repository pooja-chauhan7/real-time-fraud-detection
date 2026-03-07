# Real-Time Fraud Detection System

A professional-grade fraud detection dashboard for monitoring banking transactions in real-time. Built for a college competition with a modern fintech-style UI.

## Features

### ✅ Fixed Issues
1. **Dashboard Glitch Fixed** - No more refresh/restart loops
2. **Stable Connection** - Proper connection status handling
3. **Working Fraud Detection** - Triggers on:
   - Transaction amount ≥ ₹50,000
   - Sudden location changes
   - Multiple rapid transactions
   - Suspicious bank statement patterns
4. **Professional UI** - Dark blue banking theme with glassmorphism
5. **Real-Time Updates** - Live transaction and alert monitoring

### Dashboard Features
- **Top Stats Cards**: Total Transactions, Fraudulent Transactions, Fraud Alerts, Fraud Rate
- **Charts**: Fraud vs Normal Transactions (Pie), Transaction Trends (Line), Volume (Bar)
- **Transaction Table**: Real-time transactions with status badges
- **Alerts Panel**: Live fraud alerts with risk levels
- **OTP Verification**: Mobile verification for fraud alerts
- **Bank Statement Upload**: CSV upload with fraud analysis

## Quick Start

### Prerequisites
- Python 3.8+
- Web browser (Chrome/Firefox/Edge)

### Installation

1. **Install Python Dependencies**
```bash
pip install -r requirements.txt
```

2. **Start the Backend API**
```bash
# Option 1: Using Python directly
python api/app.py

# Option 2: Using the batch file (Windows)
start_backend.bat
```

3. **Open the Dashboard**
```bash
# Open in browser
frontend_dashboard/index.html
```

Or simply open `frontend_dashboard/index.html` in your web browser.

### Default API URL
The dashboard connects to: `http://localhost:5000`

If your backend runs on a different port, update `API_BASE_URL` in `frontend_dashboard/app.js`:
```javascript
const API_BASE_URL = 'http://localhost:5000';  // Change this if needed
```

## How to Test Fraud Detection

### Method 1: Automatic Stream
The system automatically generates transactions. Wait a few minutes and you'll see:
- Normal transactions (₹1 - ₹5,000) - 50%
- Medium transactions (₹5,000 - ₹50,000) - 30%
- High-value transactions (₹50,000 - ₹150,000) - 20%

Fraud will be detected on transactions ≥ ₹50,000!

### Method 2: Manual Analysis
1. Go to the "Analyze" tab
2. Enter an amount ≥ 50000
3. Click "Analyze Transaction"
4. Watch it get flagged as FRAUD!

### Method 3: Upload Bank Statement
1. Go to "Upload Statement" tab
2. Upload a CSV file with transactions
3. Include amounts ≥ ₹50,000 to test fraud detection

## Project Structure

```
project/
├── api/
│   └── app.py              # Flask backend API
├── config.py               # Configuration settings
├── frontend_dashboard/
│   ├── index.html          # Main dashboard
│   ├── app.js             # Frontend logic
│   ├── styles.css         # Professional UI styles
│   └── charts.js          # Chart visualizations
├── models/
│   └── fraud_detector.py  # ML + Rule-based fraud detection
├── streaming/
│   └── transaction_generator.py  # Transaction simulator
├── database/
│   ├── init_db.py         # Database initialization
│   └── schema.sql         # Database schema
└── requirements.txt       # Python dependencies
```

## Database Tables (Already Created)

The system uses SQLite with these tables:
- `users` - User accounts
- `verified_users` - Mobile-verified users
- `otp_store` - OTP verification codes
- `transactions` - All transactions with fraud status
- `alerts` - Fraud alerts
- `bank_statements` - Uploaded statement analysis
- `activity_logs` - Activity history

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stats` | GET | Dashboard statistics |
| `/api/transactions` | GET | Transaction list |
| `/api/alerts` | GET | Fraud alerts |
| `/api/analyze` | POST | Analyze a transaction |
| `/api/start-stream` | POST | Start transaction stream |
| `/api/stop-stream` | POST | Stop transaction stream |
| `/api/upload-statement` | POST | Upload bank statement CSV |
| `/api/send-otp` | POST | Send OTP for verification |
| `/api/verify-otp` | POST | Verify OTP code |

## Professional UI Features

- **Dark Blue Banking Theme** - Modern fintech aesthetic
- **Glassmorphism Effects** - Frosted glass card design
- **Smooth Animations** - Hover effects and transitions
- **Responsive Design** - Works on all screen sizes
- **Real-Time Updates** - Live data without page refresh
- **Professional Typography** - Inter font family

## Troubleshooting

### Backend won't start
```bash
# Check if port 5000 is in use
netstat -ano | findstr 5000

# Kill process if needed
taskkill /PID <PID> /F
```

### Dashboard shows "Disconnected"
1. Make sure the backend is running (`python api/app.py`)
2. Check the API URL in app.js matches your port
3. Check console for CORS errors

### No fraud detected
- Wait for the stream to generate high-value transactions (takes 1-2 minutes)
- Use manual analysis with amount ≥ ₹50,000
- Check browser console for transaction logs

### Database errors
- Delete `api/fraud_detection.db` to reset
- Restart the backend to reinitialize

## Competition Ready! 🎓

This dashboard is now:
- ✅ Professional and impressive UI
- ✅ Working fraud detection
- ✅ Real-time updates
- ✅ Stable and bug-free
- ✅ Easy to demonstrate



