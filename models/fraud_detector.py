"""
Fraud Detector Module
Machine Learning model for detecting fraudulent bank transactions
Uses a combination of rule-based and ML-based fraud detection
"""

import pickle
import logging
import os
from datetime import datetime
from typing import Dict, Optional, List
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FraudDetector:
    """
    Real-time fraud detection using trained ML model.
    Provides methods to predict fraudulent transactions.
    """
    
    def __init__(self, model_path: str = None):
        """
        Initialize the fraud detector.
        
        Args:
            model_path: Path to the trained model file (optional)
        """
        self.model = None
        self.scaler = None
        self.model_path = model_path
        self.initialized = False
        self.feature_columns = ['amount', 'card_present', 'hour_of_day', 'day_of_week']
        
        # Try to load model if path provided
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
    
    def load_model(self, model_path: str):
        """
        Load a pre-trained fraud detection model.
        
        Args:
            model_path: Path to the model file
        """
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
                
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_columns = model_data.get('feature_columns', self.feature_columns)
            self.trained_at = model_data.get('trained_at', 'Unknown')
            
            self.initialized = True
            logger.info(f"ML Model loaded successfully from {model_path}")
            logger.info(f"Model trained at: {self.trained_at}")
            logger.info(f"Feature columns: {self.feature_columns}")
            
        except Exception as e:
            logger.warning(f"Failed to load ML model: {e}. Using rule-based detection.")
            self.initialized = False
    
    def _extract_features(self, transaction: Dict) -> np.ndarray:
        """
        Extract features from transaction data.
        
        Args:
            transaction: Transaction dictionary
            
        Returns:
            Feature vector as numpy array
        """
        # Parse timestamp to extract hour and day of week
        timestamp_str = transaction.get('timestamp', '')
        if timestamp_str:
            try:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                hour_of_day = dt.hour
                day_of_week = dt.weekday() + 1  # Monday = 1
            except:
                hour_of_day = datetime.now().hour
                day_of_week = datetime.now().weekday() + 1
        else:
            hour_of_day = datetime.now().hour
            day_of_week = datetime.now().weekday() + 1
            
        # Prepare feature vector
        features = [
            float(transaction.get('amount', 0)),
            1 if transaction.get('card_present', True) else 0,
            float(hour_of_day),
            float(day_of_week)
        ]
        
        return np.array(features).reshape(1, -1)
    
    def _rule_based_detection(self, transaction: Dict) -> Dict:
        """
        Rule-based fraud detection.
        
        Args:
            transaction: Transaction dictionary
            
        Returns:
            Dictionary with rule-based detection results
        """
        is_fraud = False
        reasons = []
        fraud_probability = 0.0
        
        amount = transaction.get('amount', 0)
        card_present = transaction.get('card_present', True)
        
        # Rule 1: High amount check (> $5000)
        if amount > 5000:
            is_fraud = True
            reasons.append("High transaction amount (>$5000)")
            fraud_probability = max(fraud_probability, 0.85)
        
        # Rule 2: Card not present + high amount (> $1000)
        if not card_present and amount > 1000:
            is_fraud = True
            reasons.append("Card not present for high amount (>$1000)")
            fraud_probability = max(fraud_probability, 0.75)
        
        # Rule 3: Very high amount (> $8000)
        if amount > 8000:
            is_fraud = True
            reasons.append("Very high amount (>$8000)")
            fraud_probability = max(fraud_probability, 0.95)
        
        # Rule 4: Extremely high amount (> $9500)
        if amount > 9500:
            is_fraud = True
            reasons.append("Extremely high amount (>$9500)")
            fraud_probability = 0.98
        
        # Rule 5: Unusual time (late night)
        try:
            timestamp_str = transaction.get('timestamp', '')
            if timestamp_str:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                if dt.hour < 5 or dt.hour > 23:
                    reasons.append("Transaction at unusual hour")
                    fraud_probability = max(fraud_probability, 0.3)
        except:
            pass
        
        # Rule 6: Multiple rapid transactions from same user
        # (This would require checking transaction history)
        
        return {
            'is_fraud': is_fraud,
            'fraud_probability': min(fraud_probability, 1.0),
            'reasons': reasons,
            'method': 'rule_based'
        }
    
    def predict(self, transaction: Dict) -> Dict:
        """
        Predict whether a transaction is fraudulent.
        
        Args:
            transaction: Transaction dictionary containing:
                - amount: Transaction amount
                - card_present: Whether card was physically present
                - timestamp: Transaction timestamp (ISO format)
                
        Returns:
            Dictionary with prediction results:
                - is_fraud: Boolean indicating fraud
                - fraud_probability: Probability of fraud (0-1)
                - confidence: Prediction confidence
                - reasons: List of fraud indicators
        """
        # Start with rule-based detection
        rule_result = self._rule_based_detection(transaction)
        
        # If ML model is available, combine with ML predictions
        if self.initialized and self.model is not None:
            try:
                # Extract features
                features = self._extract_features(transaction)
                
                # Scale features
                features_scaled = self.scaler.transform(features)
                
                # Get ML prediction
                ml_prediction = self.model.predict(features_scaled)[0]
                ml_probability = self.model.predict_proba(features_scaled)[0]
                
                # Combine rule-based and ML results
                ml_fraud_prob = float(ml_probability[1])
                
                # Use weighted average (60% ML, 40% rules)
                combined_probability = (0.6 * ml_fraud_prob) + (0.4 * rule_result['fraud_probability'])
                
                # Determine final prediction
                is_fraud = bool(ml_prediction) or combined_probability > 0.5
                
                result = {
                    'is_fraud': is_fraud,
                    'fraud_probability': combined_probability,
                    'ml_probability': ml_fraud_prob,
                    'rule_probability': rule_result['fraud_probability'],
                    'confidence': max(ml_fraud_prob, 1 - ml_fraud_prob),
                    'reasons': rule_result['reasons'],
                    'method': 'hybrid'
                }
                
            except Exception as e:
                logger.error(f"ML prediction error: {e}. Using rule-based only.")
                result = rule_result
        else:
            # Use rule-based detection only
            result = rule_result
        
        # Add risk level
        result['risk_level'] = self._calculate_risk_level(result['fraud_probability'])
        
        # Log high-risk transactions
        if result['is_fraud']:
            logger.warning(
                f"FRAUD DETECTED: {transaction.get('transaction_id', 'UNKNOWN')} - "
                f"Amount: ${transaction.get('amount', 0):.2f}, "
                f"Probability: {result['fraud_probability']:.2%}, "
                f"Reasons: {', '.join(result['reasons'])}"
            )
        
        return result
    
    def analyze_transaction(self, transaction: Dict) -> Dict:
        """
        Perform comprehensive analysis on a transaction.
        
        Args:
            transaction: Transaction dictionary
            
        Returns:
            Dictionary with transaction details and fraud analysis
        """
        # Get prediction
        prediction = self.predict(transaction)
        
        # Add transaction details
        analysis = {
            'transaction_id': transaction.get('transaction_id'),
            'user_id': transaction.get('user_id'),
            'amount': transaction.get('amount'),
            'location': transaction.get('location'),
            'merchant': transaction.get('merchant'),
            'timestamp': transaction.get('timestamp'),
            **prediction
        }
        
        return analysis
    
    def _calculate_risk_level(self, fraud_probability: float) -> str:
        """
        Calculate risk level based on fraud probability.
        
        Args:
            fraud_probability: Probability of fraud (0-1)
            
        Returns:
            Risk level: LOW, MEDIUM, HIGH, or CRITICAL
        """
        if fraud_probability >= 0.8:
            return 'CRITICAL'
        elif fraud_probability >= 0.6:
            return 'HIGH'
        elif fraud_probability >= 0.4:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def batch_predict(self, transactions: List[Dict]) -> List[Dict]:
        """
        Predict fraud for a batch of transactions.
        
        Args:
            transactions: List of transaction dictionaries
            
        Returns:
            List of prediction results
        """
        return [self.analyze_transaction(txn) for txn in transactions]


# Factory function to create detector
def create_fraud_detector(model_path: str = None) -> FraudDetector:
    """
    Create a fraud detector instance.
    
    Args:
        model_path: Optional path to trained model
        
    Returns:
        FraudDetector instance
    """
    return FraudDetector(model_path=model_path)


# Example usage
if __name__ == "__main__":
    # Test with sample transactions
    detector = FraudDetector()
    
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
    print("Normal Transaction Test:")
    print("=" * 50)
    result = detector.analyze_transaction(normal_txn)
    print(f"Transaction: {result['transaction_id']}")
    print(f"Amount: ${result['amount']}")
    print(f"Is Fraud: {result['is_fraud']}")
    print(f"Fraud Probability: {result['fraud_probability']:.2%}")
    print(f"Risk Level: {result['risk_level']}")
    print(f"Reasons: {result.get('reasons', [])}")
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
    print("Suspicious Transaction Test:")
    print("=" * 50)
    result = detector.analyze_transaction(suspicious_txn)
    print(f"Transaction: {result['transaction_id']}")
    print(f"Amount: ${result['amount']}")
    print(f"Is Fraud: {result['is_fraud']}")
    print(f"Fraud Probability: {result['fraud_probability']:.2%}")
    print(f"Risk Level: {result['risk_level']}")
    print(f"Reasons: {result.get('reasons', [])}")

