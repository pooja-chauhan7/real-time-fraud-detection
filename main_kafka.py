"""
Main Application - Full Version with Kafka and Spark
Real-Time Fraud Detection System

This version requires Kafka, Zookeeper, and optionally Spark.
For full streaming architecture demonstration.

Usage:
    # First, start Kafka and Zookeeper (via docker-compose)
    docker-compose -f docker/docker-compose.yml up -d
    
    # Then run this application
    python main_kafka.py
"""

import os
import sys
import threading
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
from api.app import create_app
from models.fraud_detector import FraudDetector
from streaming.transaction_generator import TransactionGenerator

# Try to import Kafka components
try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.warning("Kafka libraries not installed. Running in simulation mode.")


class FraudDetectionSystemWithKafka:
    """
    Full fraud detection system with Kafka integration.
    Streams transactions through Kafka topic.
    """
    
    def __init__(self):
        self.app = None
        self.fraud_detector = None
        self.transaction_generator = None
        self.kafka_producer = None
        self.transactions = []
        self.alerts = []
        self.running = False
        self.use_kafka = False
        
    def initialize(self):
        """Initialize all components"""
        logger.info("Initializing Fraud Detection System (Kafka Version)...")
        
        # Initialize fraud detector
        self.fraud_detector = FraudDetector(config.MODEL_PATH)
        logger.info(f"Fraud detector initialized: {'ML Model Loaded' if self.fraud_detector.initialized else 'Rule-based'}")
        
        # Initialize transaction generator
        self.transaction_generator = TransactionGenerator()
        logger.info("Transaction generator initialized")
        
        # Try to initialize Kafka producer
        if KAFKA_AVAILABLE:
            try:
                self.kafka_producer = KafkaProducer(
                    bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: str(v).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None,
                    acks='all',
                    compression_type='gzip'
                )
                self.use_kafka = True
                logger.info(f"Kafka producer connected to {config.KAFKA_BOOTSTRAP_SERVERS}")
            except Exception as e:
                logger.warning(f"Failed to connect to Kafka: {e}. Running in simulation mode.")
                self.use_kafka = False
        else:
            logger.info("Running in simulation mode (no Kafka)")
        
        # Initialize Flask app
        self.app = create_app()
        logger.info("Flask API initialized")
        
    def publish_to_kafka(self, transaction):
        """Publish transaction to Kafka topic"""
        if not self.use_kafka or not self.kafka_producer:
            return False
            
        try:
            future = self.kafka_producer.send(
                config.KAFKA_TOPIC,
                key=transaction['transaction_id'],
                value=transaction
            )
            # Wait for send to complete (optional, for testing)
            # record_metadata = future.get(timeout=10)
            return True
        except KafkaError as e:
            logger.error(f"Failed to publish to Kafka: {e}")
            return False
    
    def generate_and_stream_transactions(self):
        """Generate and stream transactions"""
        logger.info("Starting transaction stream...")
        
        while self.running:
            try:
                # Generate a transaction
                transaction = self.transaction_generator.generate_transaction()
                
                # Process through fraud detection
                result = self.fraud_detector.analyze_transaction(transaction)
                
                # Add fraud detection results
                transaction['is_fraud'] = result['is_fraud']
                transaction['fraud_probability'] = result['fraud_probability']
                transaction['risk_level'] = result['risk_level']
                transaction['reasons'] = result.get('reasons', [])
                transaction['processed_at'] = datetime.now().isoformat()
                
                # Publish to Kafka if available
                if self.use_kafka:
                    self.publish_to_kafka(transaction)
                
                # Store transaction locally
                self.transactions.append(transaction)
                
                # Limit stored transactions
                if len(self.transactions) > 1000:
                    self.transactions.pop(0)
                
                # Create alert if fraud detected
                if transaction['is_fraud']:
                    alert = {
                        'transaction_id': transaction['transaction_id'],
                        'user_id': transaction['user_id'],
                        'amount': transaction['amount'],
                        'timestamp': transaction['timestamp'],
                        'alert_time': transaction['processed_at'],
                        'status': 'new',
                        'risk_level': transaction['risk_level'],
                        'reasons': transaction['reasons']
                    }
                    self.alerts.append(alert)
                    
                    # Log fraud detection
                    logger.warning(
                        f"🚨 FRAUD DETECTED: {transaction['transaction_id']} - "
                        f"${transaction['amount']:.2f}"
                    )
                    
                    # Publish alert to Kafka
                    if self.use_kafka:
                        try:
                            self.kafka_producer.send(
                                config.KAFKA_ALERTS_TOPIC,
                                key=alert['transaction_id'],
                                value=alert
                            )
                        except Exception as e:
                            logger.error(f"Failed to publish alert: {e}")
                else:
                    # Log normal transaction
                    logger.info(f"✓ Normal: {transaction['transaction_id']} - ${transaction['amount']:.2f}")
                
                # Update Flask app's data
                if self.app:
                    self.app.config['transactions'] = self.transactions
                    self.app.config['alerts'] = self.alerts
                
                # Wait before next transaction
                time.sleep(1.0 / config.TRANSACTIONS_PER_SECOND)
                
            except Exception as e:
                logger.error(f"Error in transaction stream: {e}")
                time.sleep(1)
    
    def start(self):
        """Start the fraud detection system"""
        self.initialize()
        self.running = True
        
        # Start transaction generator in background thread
        stream_thread = threading.Thread(
            target=self.generate_and_stream_transactions, 
            daemon=True
        )
        stream_thread.start()
        
        # Print startup banner
        kafka_status = "Connected" if self.use_kafka else "Simulation Mode"
        
        print("\n" + "=" * 60)
        print("   🛡️  REAL-TIME FRAUD DETECTION SYSTEM  🛡️")
        print("              (Kafka Full Version)")
        print("=" * 60)
        print(f"\n📊 System Configuration:")
        print(f"   • Transactions/second: {config.TRANSACTIONS_PER_SECOND}")
        print(f"   • Max transaction amount: ${config.MAX_TRANSACTION_AMOUNT}")
        print(f"   • ML Model: {'Loaded' if self.fraud_detector.initialized else 'Rule-based'}")
        print(f"   • Kafka: {kafka_status}")
        if self.use_kafka:
            print(f"   • Kafka Broker: {config.KAFKA_BOOTSTRAP_SERVERS}")
            print(f"   • Topic: {config.KAFKA_TOPIC}")
        print(f"\n🌐 Services:")
        print(f"   • API Server: http://localhost:{config.API_PORT}")
        print(f"   • Dashboard: Open frontend/index.html in browser")
        print(f"\n📝 Quick Start:")
        print(f"   1. Open http://localhost:{config.API_PORT} to test API")
        print(f"   2. Open frontend/index.html for the dashboard")
        print(f"\n⚠️  Press Ctrl+C to stop\n")
        print("=" * 60 + "\n")
        
        # Run Flask app
        try:
            self.app.run(
                host=config.API_HOST,
                port=config.API_PORT,
                debug=config.API_DEBUG,
                threaded=True,
                use_reloader=False
            )
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the fraud detection system"""
        logger.info("Stopping Fraud Detection System...")
        self.running = False
        
        if self.kafka_producer:
            self.kafka_producer.flush()
            self.kafka_producer.close()
            
        print("\n🛑 System stopped.")


def main():
    """Main entry point"""
    system = FraudDetectionSystemWithKafka()
    system.start()


if __name__ == "__main__":
    main()

