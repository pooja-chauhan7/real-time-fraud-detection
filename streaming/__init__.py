"""
Streaming Package - Kafka and Transaction Streaming Components
"""

from .transaction_generator import TransactionGenerator
from .fraud_detector_integration import process_transaction_with_fraud_detection

__all__ = ['TransactionGenerator', 'process_transaction_with_fraud_detection']

