"""
Configuration file for Real-Time Fraud Detection System
Unified configuration for both simplified and full versions
"""

import os
from datetime import datetime

# ==================== API Configuration ====================
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', 5000))
API_DEBUG = True

# ==================== Kafka Configuration ====================
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_TOPIC = 'bank-transactions'
KAFKA_CONSUMER_GROUP = 'fraud-detection-group'
KAFKA_TRANSACTIONS_TOPIC = 'bank-transactions'
KAFKA_PROCESSED_TOPIC = 'processed-transactions'
KAFKA_ALERTS_TOPIC = 'fraud-alerts'

# ==================== Transaction Generation ====================
TRANSACTIONS_PER_SECOND = 3
MAX_TRANSACTION_AMOUNT = 10000
LOCATIONS = [
    "New York, USA", "Los Angeles, USA", "Chicago, USA", "Houston, USA",
    "Phoenix, USA", "London, UK", "Paris, France", "Berlin, Germany",
    "Tokyo, Japan", "Sydney, Australia", "Toronto, Canada", "Mumbai, India"
]

MERCHANTS = [
    "Amazon", "Walmart", "Target", "Best Buy", "Apple Store",
    "Starbucks", "McDonalds", "Netflix", "Spotify", "Uber",
    "Airbnb", "DoorDash", "Google Pay", "PayPal", "Venmo"
]

USER_IDS = [f"USER{str(i).zfill(3)}" for i in range(1, 101)]

# ==================== ML Model Configuration ====================
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'fraud_model.pkl')
FRAUD_THRESHOLD = 0.5

# ==================== Spark Configuration ====================
SPARK_APP_NAME = 'FraudDetectionStreaming'
SPARK_CHECKPOINT_DIR = './checkpoint'
SPARK_MASTER = 'local[*]'

# ==================== MongoDB Configuration ====================
MONGO_HOST = os.getenv('MONGO_HOST', 'localhost')
MONGO_PORT = int(os.getenv('MONGO_PORT', 27017))
MONGO_USER = os.getenv('MONGO_USER', 'admin')
MONGO_PASSWORD = os.getenv('MONGO_PASSWORD', 'password')
MONGO_DB = os.getenv('MONGO_DB', 'fraud_detection')

def get_mongo_uri():
    """Get MongoDB connection URI"""
    return f"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}/"

def get_current_timestamp():
    """Get current timestamp in ISO format"""
    return datetime.now().isoformat()

# ==================== Dashboard Configuration ====================
DASHBOARD_REFRESH_INTERVAL = 3000  # milliseconds
MAX_TRANSACTIONS_DISPLAY = 100
MAX_ALERTS_DISPLAY = 50

# ==================== OTP Configuration ====================
OTP_EXPIRY_SECONDS = 300  # 5 minutes
OTP_LENGTH = 6

# ==================== SMS Simulation Configuration ====================
SMS_SIMULATION_ENABLED = True
SMS_SIMULATION_LOG = True  # Print SMS to console

# ==================== Email Alert Configuration ====================
EMAIL_ENABLED = True  # Set to False to disable email alerts
EMAIL_SIMULATION = True  # Set to True to simulate emails (print to console)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_USERNAME = os.getenv('EMAIL_USERNAME', 'your-email@gmail.com')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', 'your-app-password')
EMAIL_FROM = os.getenv('EMAIL_FROM', 'Fraud Detection <noreply@frauddetection.com>')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'admin@example.com')

# ==================== Fraud Detection - Call Features ====================
# Maximum calls to unknown numbers before marking as suspicious
MAX_UNKNOWN_CALLS_PER_HOUR = 5
# Time window for suspicious pattern detection (in minutes)
SUSPICIOUS_TIME_WINDOW_MINUTES = 60
# OTP expiry for call verification (in seconds)
CALL_OTP_EXPIRY_SECONDS = 120  # 2 minutes for call OTP

# ==================== Known Contacts ====================
# Users with these contact patterns are considered known
KNOWN_CONTACT_THRESHOLD = 3  # Number of calls to mark as known

