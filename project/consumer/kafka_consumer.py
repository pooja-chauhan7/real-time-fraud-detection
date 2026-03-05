"""
Kafka Consumer Module
Consumes bank transaction stream from Kafka topic
"""

import json
import logging
from typing import Callable, Optional
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BankTransactionConsumer:
    """
    Kafka consumer for reading bank transactions from Kafka topic.
    Supports batch processing and custom message handlers.
    """
    
    def __init__(self,
                 bootstrap_servers: str = config.KAFKA_BOOTSTRAP_SERVERS,
                 topic: str = config.KAFKA_TOPIC,
                 group_id: str = config.KAFKA_CONSUMER_GROUP,
                 auto_offset_reset: str = 'earliest'):
        """
        Initialize the Kafka consumer.
        
        Args:
            bootstrap_servers: Kafka broker address
            topic: Kafka topic to subscribe to
            group_id: Consumer group ID
            auto_offset_reset: Where to start reading ('earliest' or 'latest')
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.auto_offset_reset = auto_offset_reset
        self.consumer: Optional[KafkaConsumer] = None
        self.message_handler: Optional[Callable] = None
        self.running = False
        self.messages_processed = 0
        
    def create_consumer(self) -> KafkaConsumer:
        """
        Create and configure Kafka consumer.
        
        Returns:
            KafkaConsumer: Configured Kafka consumer instance
        """
        try:
            consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset=self.auto_offset_reset,
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                max_poll_records=100,
                max_poll_interval_ms=300000,
                heartbeat_interval_ms=30000
            )
            logger.info(f"Kafka consumer connected to {self.bootstrap_servers}")
            logger.info(f"Subscribed to topic: {self.topic}")
            return consumer
        except KafkaError as e:
            logger.error(f"Failed to create Kafka consumer: {e}")
            raise
            
    def set_message_handler(self, handler: Callable):
        """
        Set custom message handler function.
        
        Args:
            handler: Function to call for each message
        """
        self.message_handler = handler
        
    def process_message(self, message):
        """
        Process a single Kafka message.
        
        Args:
            message: Kafka message object
            
        Returns:
            Processed transaction data
        """
        transaction = message.value
        self.messages_processed += 1
        
        # Call custom handler if set
        if self.message_handler:
            return self.message_handler(transaction)
            
        return transaction
        
    def consume(self, max_messages: int = None):
        """
        Start consuming messages from Kafka topic.
        
        Args:
            max_messages: Maximum messages to process (None for unlimited)
        """
        self.running = True
        self.consumer = self.create_consumer()
        
        logger.info("Starting to consume messages...")
        processed = 0
        
        try:
            for message in self.consumer:
                if not self.running:
                    break
                    
                self.process_message(message)
                processed += 1
                
                # Log progress
                if processed % 100 == 0:
                    logger.info(f"Processed {processed} messages")
                    
                # Check if we've reached max_messages
                if max_messages and processed >= max_messages:
                    logger.info(f"Reached max messages limit: {max_messages}")
                    break
                    
        except KeyboardInterrupt:
            logger.info("Consumer interrupted")
        except Exception as e:
            logger.error(f"Error consuming messages: {e}")
        finally:
            self.close()
            
    def consume_batch(self, batch_size: int = 100, timeout: int = 30):
        """
        Consume messages in batches.
        
        Args:
            batch_size: Number of messages per batch
            timeout: Timeout in seconds
            
        Returns:
            List of transaction dictionaries
        """
        self.consumer = self.create_consumer()
        batch = []
        
        logger.info(f"Waiting for batch of {batch_size} messages...")
        
        try:
            # Poll for messages
            while len(batch) < batch_size:
                records = self.consumer.poll(timeout_ms=timeout * 1000)
                
                for topic_partition, messages in records.items():
                    for message in messages:
                        batch.append(message.value)
                        if len(batch) >= batch_size:
                            break
                    if len(batch) >= batch_size:
                        break
                        
            logger.info(f"Received batch of {len(batch)} messages")
            return batch
            
        except Exception as e:
            logger.error(f"Error consuming batch: {e}")
            return batch
        finally:
            self.close()
            
    def stop(self):
        """Stop consuming messages"""
        self.running = False
        
    def close(self):
        """Close the consumer"""
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")
            
    def get_stats(self) -> dict:
        """Get consumer statistics"""
        return {
            'messages_processed': self.messages_processed,
            'topic': self.topic,
            'group_id': self.group_id
        }


# Example message handler
def fraud_check_handler(transaction: dict) -> dict:
    """
    Example message handler that performs basic fraud checks.
    
    Args:
        transaction: Transaction dictionary
        
    Returns:
        Transaction with fraud indicators
    """
    # Check for suspicious patterns
    is_suspicious = False
    reasons = []
    
    # High amount check
    if transaction.get('amount', 0) > 5000:
        is_suspicious = True
        reasons.append("High transaction amount")
        
    # Card not present check
    if not transaction.get('card_present', True):
        is_suspicious = True
        reasons.append("Card not present")
        
    transaction['is_suspicious'] = is_suspicious
    transaction['suspicion_reasons'] = reasons
    
    return transaction


def main():
    """Main function to run the consumer"""
    consumer = BankTransactionConsumer()
    consumer.set_message_handler(fraud_check_handler)
    
    try:
        # Consume messages
        consumer.consume(max_messages=50)
        
    except KeyboardInterrupt:
        logger.info("Shutting down consumer...")
    finally:
        consumer.close()


if __name__ == "__main__":
    main()

