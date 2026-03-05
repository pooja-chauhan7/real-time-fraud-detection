-- MongoDB Schema Definition for Fraud Detection System
-- This file contains collection schemas and index definitions

-- Transactions Collection
db.transactions.createIndex({ "transaction_id": 1 }, { unique: true })
db.transactions.createIndex({ "user_id": 1 })
db.transactions.createIndex({ "timestamp": -1 })
db.transactions.createIndex({ "is_fraud": 1 })
db.transactions.createIndex({ "amount": 1 })
db.transactions.createIndex({ "location": 1 })

-- Alerts Collection
db.alerts.createIndex({ "transaction_id": 1 }, { unique: true })
db.alerts.createIndex({ "alert_time": -1 })
db.alerts.createIndex({ "status": 1 })
db.alerts.createIndex({ "user_id": 1 })

-- Users Collection (optional - for user history)
db.users.createIndex({ "user_id": 1 }, { unique: true })
db.users.createIndex({ "created_at": -1 })

-- Example Document Structures:

-- Transaction Document:
{
    "transaction_id": "TXN123456",
    "user_id": "USER001",
    "amount": 150.00,
    "location": "New York, USA",
    "timestamp": "2024-01-15T10:30:00",
    "merchant": "Amazon",
    "card_present": true,
    "is_fraud": false,
    "fraud_probability": 0.15,
    "processed_timestamp": "2024-01-15T10:30:05"
}

-- Alert Document:
{
    "transaction_id": "TXN123456",
    "user_id": "USER001",
    "amount": 9500.00,
    "timestamp": "2024-01-15T10:30:00",
    "alert_time": "2024-01-15T10:30:05",
    "status": "new",
    "risk_level": "HIGH",
    "description": "High amount transaction detected",
    "indicators": [
        {
            "type": "HIGH_AMOUNT",
            "severity": "HIGH",
            "description": "Transaction amount $9500.00 exceeds $5000"
        },
        {
            "type": "CARD_NOT_PRESENT",
            "severity": "MEDIUM",
            "description": "Card was not physically present"
        }
    ]
}

-- User Document:
{
    "user_id": "USER001",
    "name": "John Doe",
    "email": "john@example.com",
    "account_created": "2023-01-01",
    "total_transactions": 150,
    "fraud_count": 2,
    "risk_score": 0.15
}

