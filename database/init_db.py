"""
Database Initialization Script
Initializes MongoDB database with collections and indexes
"""

import logging
from pymongo import MongoClient
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_database():
    """Initialize MongoDB database with collections and indexes"""
    
    try:
        # Connect to MongoDB
        client = MongoClient(config.get_mongo_uri())
        db = client[config.MONGO_DB]
        
        logger.info(f"Connected to MongoDB: {config.MONGO_DB}")
        
        # Create collections
        collections = ['transactions', 'alerts', 'users']
        for collection in collections:
            if collection not in db.list_collection_names():
                db.create_collection(collection)
                logger.info(f"Created collection: {collection}")
            else:
                logger.info(f"Collection already exists: {collection}")
        
        # Create indexes for transactions collection
        transactions = db.transactions
        transactions.create_index("transaction_id", unique=True)
        transactions.create_index("user_id")
        transactions.create_index("timestamp")
        transactions.create_index("is_fraud")
        transactions.create_index([("timestamp", -1)])
        
        logger.info("Created indexes for transactions collection")
        
        # Create indexes for alerts collection
        alerts = db.alerts
        alerts.create_index("transaction_id", unique=True)
        alerts.create_index("alert_time")
        alerts.create_index("status")
        
        logger.info("Created indexes for alerts collection")
        
        # Create sample data (optional)
        create_sample_data(db)
        
        logger.info("Database initialization complete!")
        
        return db
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def create_sample_data(db):
    """Create sample transaction data for testing"""
    
    from datetime import datetime, timedelta
    import random
    
    # Check if data already exists
    if db.transactions.count_documents({}) > 0:
        logger.info("Sample data already exists, skipping...")
        return
    
    logger.info("Creating sample data...")
    
    sample_transactions = [
        {
            'transaction_id': 'TXN_SAMPLE_001',
            'user_id': 'USER001',
            'amount': 150.00,
            'location': 'New York, USA',
            'timestamp': datetime.now().isoformat(),
            'merchant': 'Amazon',
            'card_present': True,
            'is_fraud': False
        },
        {
            'transaction_id': 'TXN_SAMPLE_002',
            'user_id': 'USER002',
            'amount': 9500.00,
            'location': 'Unknown',
            'timestamp': (datetime.now() - timedelta(hours=1)).isoformat(),
            'merchant': 'Unknown',
            'card_present': False,
            'is_fraud': True
        },
        {
            'transaction_id': 'TXN_SAMPLE_003',
            'user_id': 'USER003',
            'amount': 75.50,
            'location': 'Los Angeles, USA',
            'timestamp': (datetime.now() - timedelta(hours=2)).isoformat(),
            'merchant': 'Starbucks',
            'card_present': True,
            'is_fraud': False
        },
        {
            'transaction_id': 'TXN_SAMPLE_004',
            'user_id': 'USER004',
            'amount': 6200.00,
            'location': 'Tokyo, Japan',
            'timestamp': (datetime.now() - timedelta(hours=3)).isoformat(),
            'merchant': 'Unknown',
            'card_present': False,
            'is_fraud': True
        },
        {
            'transaction_id': 'TXN_SAMPLE_005',
            'user_id': 'USER005',
            'amount': 45.00,
            'location': 'London, UK',
            'timestamp': (datetime.now() - timedelta(hours=4)).isoformat(),
            'merchant': 'Netflix',
            'card_present': True,
            'is_fraud': False
        }
    ]
    
    # Insert sample transactions
    db.transactions.insert_many(sample_transactions)
    logger.info(f"Inserted {len(sample_transactions)} sample transactions")
    
    # Create sample alerts for fraud transactions
    fraud_transactions = [t for t in sample_transactions if t['is_fraud']]
    
    sample_alerts = []
    for txn in fraud_transactions:
        alert = {
            'transaction_id': txn['transaction_id'],
            'user_id': txn['user_id'],
            'amount': txn['amount'],
            'timestamp': txn['timestamp'],
            'alert_time': txn['timestamp'],
            'status': 'new',
            'risk_level': 'HIGH',
            'description': f"High amount transaction detected: ${txn['amount']}"
        }
        sample_alerts.append(alert)
    
    if sample_alerts:
        db.alerts.insert_many(sample_alerts)
        logger.info(f"Inserted {len(sample_alerts)} sample alerts")


def main():
    """Main function"""
    init_database()


if __name__ == "__main__":
    main()

