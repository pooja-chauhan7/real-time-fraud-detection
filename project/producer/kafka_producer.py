"""
Kafka Producer Module
Publishes bank transaction stream to Kafka topic
"""

import json
import time
import logging
import threading
from typing import Optional
from kafka import KafkaProducer
from kafka.errors import KafkaError
import config
from transaction_generator import TransactionGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BankTransactionProducer:
    """
    Kafka producer for streaming bank transactions.
    Continuously generates and publishes transactions to Kafka topic.
    """
    
    def __init__(self, 
                 bootstrap_servers: str = config.KAFKA_BOOTSTRAP_SERVERS,
                 topic: str = config.KAFKA_TOPIC):
        """
        Initialize the Kafka producer.
        
        Args:
: Kafka broker address
            topic: Kafka topic to            bootstrap_servers publish to
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.producer: Optional[KafkaProducer] = None
        self.generator = TransactionGenerator()
        self.running = False
        self.transaction_count = 0
        
    def create_producer(self) -> KafkaProducer:
        """
        Create and configure Kafka producer.
        
        Returns:
            KafkaProducer: Configured Kafka producer instance
        """
        try:
            producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas
                retries=3,
                retry_backoff_ms=1000,
                compression_type='gzip',
                linger_ms=10  # Batch messages for efficiency
            )
            logger.info(f"Kafka producer connected to {self.bootstrap_servers}")
            return producer
        except KafkaError as e:
            logger.error(f"Failed to create Kafka producer: {e}")
            raise
            
    def publish_transaction(self, transaction: dict) -> bool:
        """
        Publish a single transaction to Kafka topic.
        
        Args:
            transaction: Transaction dictionary to publish
            
        Returns:
            bool: True if published successfully, False otherwise
        """
        try:
            # Use transaction_id as key for partitioning
            future = self.producer.send(
                self.topic,
                key=transaction['transaction_id'],
                value=transaction
            )
            # Wait for send to complete (optional, for testing)
            # record_metadata = future.get(timeout=10)
            self.transaction_count += 1
            return True
        except KafkaError as e:
            logger.error(f"Failed to publish transaction: {e}")
            return False
            
    def publish_batch(self, count: int = 10) -> int:
        """
        Publish a batch of transactions.
        
        Args:
            count: Number of transactions to generate and publish
            
        Returns:
            int: Number of successfully published transactions
        """
        transactions = self.generator.generate_batch(count)
        success_count = 0
        
        for transaction in transactions:
            if self.publish_transaction(transaction):
                success_count += 1
                
        return success_count
        
    def start_streaming(self, transactions_per_second: int = None):
        """
        Start continuous streaming of transactions.
        
        Args:
            transactions_per_second: Number of transactions per second
        """
        if transactions_per_second is None:
            transactions_per_second = config.TRANSACTIONS_PER_SECOND
            
        self.running = True
        interval = 1.0 / transactions_per_second
        
        logger.info(f"Starting transaction stream: {transactions_per_second} txn/sec")
        
        while self.running:
            transaction = self.generator.generate_transaction()
            if self.publish_transaction(transaction):
                logger.debug(f"Published: {transaction['transaction_id']} - ${transaction['amount']}")
            time.sleep(interval)
            
    def start_streaming_async(self, transactions_per_second: int = None):
        """
        Start streaming in a separate thread.
        
        Args:
            transactions_per_second: Number of transactions per second
        """
        stream_thread = threading.Thread(
            target=self.start_streaming,
            args=(transactions_per_second,)
        )
        stream_thread.daemon = True
        stream_thread.start()
        return stream_thread
        
    def stop(self):
        """Stop the producer and close connections"""
        self.running = False
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("Kafka producer closed")
            
    def get_stats(self) -> dict:
        """Get producer statistics"""
        return {
            'transactions_published': self.transaction_count,
            'topic': self.topic,
            'bootstrap_servers': self.bootstrap_servers
        }


def main():
    """Main function to run the producer"""
    # Create producer
    producer = BankTransactionProducer()
    producer.producer = producer.create_producer()
    
    try:
        # Publish initial batch for testing
        logger.info("Publishing initial batch of transactions...")
        batch_size = 20
        success = producer.publish_batch(batch_size)
        logger.info(f"Published {success}/{batch_size} transactions")
        
        # Then start continuous streaming
        logger.info("Starting continuous transaction stream...")
        producer.start_streaming(transactions_per_second=5)
        
    except KeyboardInterrupt:
        logger.info("Shutting down producer...")
    finally:
        producer.stop()


if __name__ == "__main__":
    main()

