"""
Kafka Topic Manager
Creates and manages Kafka topics for the fraud detection system
"""

import logging
from kafka import KafkaAdminClient
from kafka.admin import NewTopic
from kafka.errors import KafkaError
import kafka_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TopicManager:
    """
    Manages Kafka topics for the fraud detection system.
    Creates topics if they don't exist.
    """
    
    def __init__(self, bootstrap_servers: str = None):
        self.bootstrap_servers = bootstrap_servers or kafka_config.KAFKA_BOOTSTRAP_SERVERS
        self.admin_client = None
        
    def connect(self):
        try:
            self.admin_client = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers,
                client_id='topic-manager'
            )
            logger.info(f"Connected to Kafka at {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}")
            raise
            
    def create_topics(self):
        if not self.admin_client:
            self.connect()
            
        topics = []
        
        txn_config = kafka_config.TOPIC_CONFIG['transactions']
        topics.append(NewTopic(
            name=kafka_config.TRANSACTIONS_TOPIC,
            num_partitions=txn_config['partitions'],
            replication_factor=txn_config['replication_factor']
        ))
        
        processed_config = kafka_config.TOPIC_CONFIG['processed-transactions']
        topics.append(NewTopic(
            name=kafka_config.PROCESSED_TRANSACTIONS_TOPIC,
            num_partitions=processed_config['partitions'],
            replication_factor=processed_config['replication_factor']
        ))
        
        alerts_config = kafka_config.TOPIC_CONFIG['fraud-alerts']
        topics.append(NewTopic(
            name=kafka_config.FRAUD_ALERTS_TOPIC,
            num_partitions=alerts_config['partitions'],
            replication_factor=alerts_config['replication_factor']
        ))
        
        try:
            self.admin_client.create_topics(topics)
            logger.info("Created all topics successfully")
        except KafkaError as e:
            if "TopicAlreadyExistsException" in str(e):
                logger.info("Topics already exist")
            else:
                logger.error(f"Error creating topics: {e}")
                
    def list_topics(self):
        if not self.admin_client:
            self.connect()
            
        try:
            topics = self.admin_client.list_topics()
            logger.info(f"Existing topics: {topics}")
            return topics
        except Exception as e:
            logger.error(f"Error listing topics: {e}")
            return []
            
    def close(self):
        if self.admin_client:
            self.admin_client.close()
            logger.info("Closed Kafka admin client")


if __name__ == "__main__":
    manager = TopicManager()
    try:
        manager.list_topics()
        manager.create_topics()
    finally:
        manager.close()

