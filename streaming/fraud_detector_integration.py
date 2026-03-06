"""
Fraud Detector Integration Module
Processes transactions with fraud detection
"""

import logging
from datetime import datetime
from typing import Dict, List
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.fraud_detector import FraudDetector
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_transaction_with_fraud_detection(transaction: Dict, 
                                             fraud_detector: FraudDetector = None) -> Dict:
    """
    Process a single transaction through fraud detection.
    
    Args:
        transaction: Transaction dictionary
        fraud_detector: Optional FraudDetector instance (will create if not provided)
        
    Returns:
        Transaction dictionary with fraud detection results
    """
    # Create detector if not provided
    if fraud_detector is None:
        fraud_detector = FraudDetector(config.MODEL_PATH)
    
    # Perform fraud detection
    result = fraud_detector.analyze_transaction(transaction)
    
    # Add fraud detection results to transaction
    transaction['is_fraud'] = result['is_fraud']
    transaction['fraud_probability'] = result['fraud_probability']
    transaction['risk_level'] = result['risk_level']
    transaction['reasons'] = result.get('reasons', [])
    transaction['processed_at'] = datetime.now().isoformat()
    
    # Log if fraud detected
    if transaction['is_fraud']:
        logger.warning(
            f"FRAUD DETECTED: {transaction.get('transaction_id')} - "
            f"Amount: ${transaction.get('amount', 0):.2f}, "
            f"Probability: {transaction['fraud_probability']:.2%}"
        )
    
    return transaction


def process_batch_with_fraud_detection(transactions: List[Dict],
                                        fraud_detector: FraudDetector = None) -> List[Dict]:
    """
    Process a batch of transactions through fraud detection.
    
    Args:
        transactions: List of transaction dictionaries
        fraud_detector: Optional FraudDetector instance
        
    Returns:
        List of transactions with fraud detection results
    """
    processed = []
    
    for transaction in transactions:
        processed_txn = process_transaction_with_fraud_detection(
            transaction, fraud_detector
        )
        processed.append(processed_txn)
    
    # Summary
    fraud_count = sum(1 for t in processed if t['is_fraud'])
    logger.info(
        f"Batch processed: {len(transactions)} transactions, "
        f"{fraud_count} fraud detected"
    )
    
    return processed


# Example usage
if __name__ == "__main__":
    # Test with sample transactions
    detector = FraudDetector(config.MODEL_PATH)
    
    # Test normal transaction
    normal_txn = {
        'transaction_id': 'TXN_TEST_001',
        'user_id': 'USER001',
        'amount': 50.00,
        'location': 'New York, USA',
        'merchant': 'Amazon',
        'card_present': True,
        'timestamp': datetime.now().isoformat()
    }
    
    print("=" * 50)
    print("Processing Normal Transaction:")
    print("=" * 50)
    result = process_transaction_with_fraud_detection(normal_txn, detector)
    print(f"Transaction: {result['transaction_id']}")
    print(f"Amount: ${result['amount']}")
    print(f"Is Fraud: {result['is_fraud']}")
    print(f"Fraud Probability: {result['fraud_probability']:.2%}")
    print()
    
    # Test suspicious transaction
    suspicious_txn = {
        'transaction_id': 'TXN_TEST_002',
        'user_id': 'USER002',
        'amount': 9500.00,
        'location': 'Unknown',
        'merchant': 'Unknown',
        'card_present': False,
        'timestamp': datetime.now().isoformat()
    }
    
    print("=" * 50)
    print("Processing Suspicious Transaction:")
    print("=" * 50)
    result = process_transaction_with_fraud_detection(suspicious_txn, detector)
    print(f"Transaction: {result['transaction_id']}")
    print(f"Amount: ${result['amount']}")
    print(f"Is Fraud: {result['is_fraud']}")
    print(f"Fraud Probability: {result['fraud_probability']:.2%}")
    print(f"Reasons: {result.get('reasons', [])}")

