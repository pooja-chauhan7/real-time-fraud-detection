"""
Configuration file for Fraud Detection System
Contains all configurable parameters for Kafka, MongoDB, Spark, and API
"""

import os
from datetime import datetime

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = 'bank-transactions'
KAFKA_CONSUMER_GROUP = 'fraud-detection-group'

# MongoDB Configuration
MONGO_HOST = os.getenv('MONGO_HOST', 'localhost')
MONGO_PORT = int(os.getenv('MONGO_PORT', 27017))
MONGO_DB = 'fraud_detection'
MONGO_USER = os.getenv('MONGO_USER', 'admin')
MONGO_PASSWORD = os.getenv('MONGO_PASSWORD', 'password')

# Flask API Configuration
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', 5000))
API_DEBUG = os.getenv('API_DEBUG', 'True').lower() == 'true'

# Spark Configuration
SPARK_APP_NAME = 'FraudDetectionStreaming'
SPARK_CHECKPOINT_DIR = './checkpoint'
SPARK_BATCH_INTERVAL = 5  # seconds

# ML Model Configuration
MODEL_PATH = './ml_model/model.pkl'
TRAIN_DATA_PATH = './ml_model/sample_data.csv'

# Transaction Generation
TRANSACTIONS_PER_SECOND = 5
MAX_TRANSACTION_AMOUNT = 10000

# Fraud Detection Thresholds
FRAUD_THRESHOLD = 0.5  # Probability threshold for fraud classification

# Locations for fake data generation
LOCATIONS = [
    "New York, USA",
    "Los Angeles, USA",
    "Chicago, USA",
    "Houston, USA",
    "Phoenix, USA",
    "London, UK",
    "Paris, France",
    "Berlin, Germany",
    "Tokyo, Japan",
    "Sydney, Australia"
]

# Merchants for fake data generation
MERCHANTS = [
    "Amazon",
    "Walmart",
    "Target",
    "Best Buy",
    "Apple Store",
    "Starbucks",
    "McDonald's",
    "Netflix",
    "Spotify",
    "Uber"
]

def get_mongo_uri():
    """Get MongoDB connection URI"""
    return f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}"

def get_current_timestamp():
    """Get current timestamp in ISO format"""
    return datetime.now().isoformat()

