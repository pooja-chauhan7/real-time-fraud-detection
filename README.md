# Real-Time Fraud Detection System

A complete fraud detection system that processes bank transactions and detects fraud in real-time.

## Features

- **Real-Time Transaction Processing**: Stream and analyze transactions as they happen
- **Fraud Detection**: Rule-based fraud detection with risk scoring
- **Mobile OTP Verification**: Simulated OTP verification for suspicious transactions
- **SMS Fraud Alerts**: Simulated SMS alerts for detected fraud
- **Dashboard**: Real-time dashboard with transaction monitoring
- **Analytics**: Transaction analytics and fraud trends

## Technology Stack

- **Backend**: Python (Flask)
- **Database**: SQLite
- **Frontend**: HTML/CSS/JavaScript
- **Streaming**: Transaction Generator (simulated)

## Project Structure

```
project/
├── api/
│   └── app.py              # Flask backend API
├── frontend_dashboard/
│   ├── index.html          # Dashboard UI
│   ├── app.js              # Frontend JavaScript
│   ├── charts.js           # Chart.js configuration
│   └── styles.css          # Dashboard styles
├── models/
│   └── fraud_detector.py   # ML model (rule-based)
├── streaming/
│   └── transaction_generator.py  # Transaction simulator
├── config.py               # Configuration settings
├── main.py                 # Main entry point
└── requirements.txt        # Python dependencies
```

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

### Option 1: Using the batch file (Windows)
```bash
start_backend.bat
```

### Option 2: Using Python directly
```bash
python main.py
```

## Accessing the Application

1. **API Server**: http://localhost:5000
2. **Dashboard**: Open `frontend_dashboard/index.html` in your browser

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | API health check |
| `/api/health` | System health status |
| `/api/stats` | Transaction statistics |
| `/api/transactions` | Get transaction list |
| `/api/alerts` | Get fraud alerts |
| `/api/start-stream` | Start transaction stream |
| `/api/stop-stream` | Stop transaction stream |
| `/api/send-otp` | Send OTP for verification |
| `/api/verify-otp` | Verify OTP code |
| `/api/analyze` | Analyze a single transaction |
| `/api/upload-statement` | Upload bank statement CSV |

## Dashboard Features

- **Total Transactions**: Count of all transactions
- **Fraud Transactions**: Count of detected fraudulent transactions
- **Fraud Alerts**: Active fraud alerts
- **Transaction Table**: Real-time transaction list
- **Risk Distribution**: High/Medium/Low risk breakdown

## OTP Verification

1. Click "Verify Mobile" button
2. Enter your mobile number
3. Enter the OTP received (simulated - check console logs)
4. Your number will be verified for fraud alerts

## CSV Upload Format

The system accepts CSV files with the following columns:
- `date` or `Date` or `Transaction Date`
- `amount` or `Amount` or `Debit` or `Credit`
- `type` or `Type` or `Transaction Type`
- `receiver` or `Receiver` or `To`
- `description` or `Description` or `Narration`

## Troubleshooting

### Backend won't start
- Make sure port 5000 is not in use
- Check Python dependencies are installed

### Dashboard shows "Disconnected"
- Ensure backend is running
- Refresh the page

### Transactions not appearing
- Click "Start Stream" or wait for auto-start
- Check browser console for errors

## License

MIT License

