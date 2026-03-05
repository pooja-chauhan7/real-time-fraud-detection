# Real-Time Fraud Detection System

A prototype implementation demonstrating a complete architecture for detecting fraudulent bank transactions in real-time using Apache Kafka, Apache Spark, and Machine Learning.

## Architecture Overview

```
[Kafka Producer] -> [Kafka Topic] -> [Spark Streaming] -> [ML Model] -> [MongoDB] -> [Flask API] -> [Frontend Dashboard]
```

## Project Structure

```
/project
├── producer/                    # Kafka Producer - generates fake transactions
│   ├── transaction_generator.py
│   └── kafka_producer.py
├── consumer/                    # Kafka Consumer - receives transactions
│   └── kafka_consumer.py
├── spark_processing/           # Spark Streaming - processes data
│   └── spark_processor.py
├── ml_model/                   # ML Fraud Detection Model
│   ├── train_model.py
│   ├── fraud_detector.py
│   ├── sample_data.csv
│   └── model.pkl
├── backend_api/                # Flask REST API
│   ├── app.py
│   └── requirements.txt
├── frontend_dashboard/         # Web Dashboard
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── database/                   # Database scripts
│   ├── init_db.py
│   └── schema.sql
├── docker-compose.yml          # Docker services
├── requirements.txt            # Python dependencies
└── README.md
```

## Prerequisites

- Python 3.8+
- Docker and Docker Compose
- MongoDB
- Apache Kafka
- Apache Spark

## Quick Start

### Option 1: Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# Check services
docker-compose ps
```

### Option 2: Manual Setup

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Start Kafka:**
```bash
# Using Docker
docker run -p 9092:9092 -e KAFKA_ADVERTISED_HOST_NAME=localhost -e KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181 confluentinc/cp-kafka

# Or start local Kafka cluster
```

3. **Start MongoDB:**
```bash
docker run -p 27017:27017 -e MONGO_INITDB_ROOT_USERNAME=admin -e MONGO_INITDB_ROOT_PASSWORD=password mongo
```

4. **Run the components (in separate terminals):**

```bash
# Terminal 1: Train ML Model
cd ml_model
python train_model.py

# Terminal 2: Start Kafka Producer
cd producer
python kafka_producer.py

# Terminal 3: Start Spark Processing
cd spark_processing
python spark_processor.py

# Terminal 4: Start Backend API
cd backend_api
python app.py

# Terminal 5: Start Frontend (or open in browser)
# Open frontend_dashboard/index.html in browser
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/transactions` | Get all transactions |
| GET | `/api/transactions/<id>` | Get transaction by ID |
| GET | `/api/alerts` | Get fraud alerts |
| GET | `/api/stats` | Get transaction statistics |
| POST | `/api/transactions` | Add new transaction |

## Features

- **Real-time Transaction Processing**: Streams transactions through Kafka
- **Fraud Detection**: ML-based classification using Logistic Regression
- **Live Dashboard**: Real-time updates of transactions and alerts
- **RESTful API**: Clean API for data access
- **MongoDB Storage**: Flexible document storage for transactions

## Sample Transaction Data

```json
{
  "transaction_id": "TXN123456",
  "user_id": "USER001",
  "amount": 150.00,
  "location": "New York, USA",
  "timestamp": "2024-01-15T10:30:00",
  "merchant": "Amazon",
  "card_present": true
}
```

## Configuration

Edit `config.py` to modify:
- Kafka broker address
- MongoDB connection
- Spark configurations
- API port

## License

MIT License

