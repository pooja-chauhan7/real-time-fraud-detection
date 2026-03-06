# Kafka Module for Fraud Detection System

from .kafka_config import (
    KAFKA_BOOTSTRAP_SERVERS,
    TRANSACTIONS_TOPIC,
    PROCESSED_TRANSACTIONS_TOPIC,
    FRAUD_ALERTS_TOPIC,
    get_producer_config,
    get_consumer_config,
    get_topics
)

from .topic_manager import TopicManager

__all__ = [
    'KAFKA_BOOTSTRAP_SERVERS',
    'TRANSACTIONS_TOPIC', 
    'PROCESSED_TRANSACTIONS_TOPIC',
    'FRAUD_ALERTS_TOPIC',
    'get_producer_config',
    'get_consumer_config',
    'get_topics',
    'TopicManager'
]

