"""
Database Initialization Script
Initializes SQLite database with all required tables
"""

import sqlite3
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database file path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fraud_detection.db')


def get_db_connection():
    """Get SQLite database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database with all tables"""
    
    logger.info(f"Initializing database at: {DB_PATH}")
    
    # Read schema
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Read and execute schema
        with open(schema_path, 'r') as f:
            schema = f.read()
        
        cursor.executescript(schema)
        conn.commit()
        
        logger.info("Database tables created successfully!")
        
        # Create sample data
        create_sample_data(conn)
        
        conn.close()
        
        logger.info("Database initialization complete!")
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def create_sample_data(conn):
    """Create sample data for testing"""
    
    cursor = conn.cursor()
    
    # Check if data already exists
    cursor.execute("SELECT COUNT(*) as count FROM transactions")
    if cursor.fetchone()[0] > 0:
        logger.info("Sample data already exists, skipping...")
        return
    
    logger.info("Creating sample data...")
    
    # Sample users
    sample_users = [
        ('USER001', 'John Doe', 'john@example.com', 'password123', '+1234567890'),
        ('USER002', 'Jane Smith', 'jane@example.com', 'password123', '+1234567891'),
        ('USER003', 'Bob Wilson', 'bob@example.com', 'password123', '+1234567892'),
    ]
    
    for user_id, username, email, password, mobile in sample_users:
        cursor.execute("""
            INSERT INTO users (user_id, username, email, password_hash, mobile_number, is_verified)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (user_id, username, email, password, mobile))
        
        # Add to verified users
        cursor.execute("""
            INSERT INTO verified_users (user_id, username, email, mobile_number)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, email, mobile))
    
    # Sample transactions (including some fraud)
    sample_transactions = [
        ('TXN001', 'USER001', 150.00, 'TRANSFER', 'ACC123456789', 'New York, USA', 0, 'LOW', 0.05),
        ('TXN002', 'USER002', 55000.00, 'TRANSFER', 'ACC987654321', 'Los Angeles, USA', 1, 'HIGH', 0.95, 'High amount transaction'),
        ('TXN003', 'USER001', 75.50, 'UPI', 'ACC111222333', 'New York, USA', 0, 'LOW', 0.02),
        ('TXN004', 'USER003', 120000.00, 'INTERNATIONAL', 'ACC555666777', 'Tokyo, Japan', 1, 'CRITICAL', 0.99, 'Suspicious international transaction'),
        ('TXN005', 'USER002', 45.00, 'CARD', 'ACC444555666', 'Chicago, USA', 0, 'LOW', 0.01),
        ('TXN006', 'USER001', 250.00, 'UPI', 'ACC777888999', 'Boston, USA', 0, 'LOW', 0.08),
        ('TXN007', 'USER003', 8500.00, 'TRANSFER', 'ACC111222333', 'Unknown Location', 1, 'HIGH', 0.85, 'Unusual location'),
        ('TXN008', 'USER002', 320.00, 'CARD', 'ACC444555666', 'Houston, USA', 0, 'LOW', 0.03),
    ]
    
    for txn in sample_transactions:
        cursor.execute("""
            INSERT INTO transactions (transaction_id, user_id, amount, transaction_type, 
                                    receiver_account, location, is_fraud, risk_level, 
                                    fraud_probability, fraud_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, txn)
    
    # Sample alerts for fraud transactions
    cursor.execute("""
        INSERT INTO alerts (alert_id, transaction_id, user_id, amount, alert_type, 
                          alert_message, risk_level, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ('ALT001', 'TXN002', 'USER002', 55000.00, 'HIGH_AMOUNT', 
          'Transaction amount ₹55,000 exceeds threshold of ₹50,000', 'HIGH', 'new'))
    
    cursor.execute("""
        INSERT INTO alerts (alert_id, transaction_id, user_id, amount, alert_type, 
                          alert_message, risk_level, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ('ALT002', 'TXN004', 'USER003', 120000.00, 'INTERNATIONAL_FRAUD', 
          'Suspicious international transaction detected', 'CRITICAL', 'new'))
    
    cursor.execute("""
        INSERT INTO alerts (alert_id, transaction_id, user_id, amount, alert_type, 
                          alert_message, risk_level, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, ('ALT003', 'TXN007', 'USER003', 8500.00, 'UNUSUAL_LOCATION', 
          'Transaction from unusual location', 'HIGH', 'new'))
    
    # Sample activity logs
    cursor.execute("""
        INSERT INTO activity_logs (user_id, activity_type, description)
        VALUES (?, ?, ?)
    """, ('USER001', 'LOGIN', 'User logged in successfully'))
    
    cursor.execute("""
        INSERT INTO activity_logs (user_id, activity_type, description)
        VALUES (?, ?, ?)
    """, ('USER002', 'TRANSACTION', 'Transaction of ₹55,000 flagged as fraud'))
    
    conn.commit()
    
    logger.info("Sample data created successfully!")


def main():
    """Main function"""
    init_database()


if __name__ == "__main__":
    main()

