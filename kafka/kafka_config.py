"""
Kafka Configuration and Setup
Contains Kafka broker settings and topic management
"""

import os
from typing import List

# Kafka Broker Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
KAFKA_SECURITY_PROTOCOL = 'PLAINTEXT'
KAFKA_SASL_MECHANISM = None

# Topic Configuration
TRANSACTIONS_TOPIC = 'bank-transactions'
PROCESSED_TRANSACTIONS_TOPIC = 'processed-transactions'
FRAUD_ALERTS_TOPIC = 'fraud-alerts'

# Producer Configuration
PRODUCER_CONFIG = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'client.id': 'fraud-detection-producer',
    'acks': 'all',
    'retries': 3,
    'retry.backoff.ms': 1000,
    'compression.type': 'gzip',
    'linger.ms': 10,
    'batch.size': 16384
}

# Consumer Configuration
CONSUMER_CONFIG = {
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': 'fraud-detection-group',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': True,
    'auto.commit.interval.ms': 5000,
    'max.poll.records': 100
}

# Topic Partitions and Replication
TOPIC_CONFIG = {
    'transactions': {
        'partitions': 3,
        'replication_factor': 1
    },
    'processed-transactions': {
        'partitions': 3,
        'replication_factor': 1
    },
    'fraud-alerts': {
        'partitions': 1,
        'replication_factor': 1
    }
}

def get_topics() -> List[str]:
    """Get list of all Kafka topics"""
    return [
        TRANSACTIONS_TOPIC,
        PROCESSED_TRANSACTIONS_TOPIC,
        FRAUD_ALERTS_TOPIC
    ]

def get_producer_config() -> dict:
    """Get producer configuration"""
    return PRODUCER_CONFIG.copy()

def get_consumer_config(group_id: str = 'fraud-detection-group') -> dict:
    """Get consumer configuration with custom group ID"""
    config = CONSUMER_CONFIG.copy()
    config['group.id'] = group_id
    return config

