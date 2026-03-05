"""
Fraud Detector Module
Loads and runs the trained ML model for fraud detection
"""

import pickle
import numpy as np
import logging
from datetime import datetime
from typing import Dict, Optional
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
            model_path: Path to the trained model file
        """
        self.model = None
        self.scaler = None
        self.model_path = model_path
        self.initialized = False
        
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
            self.feature_columns = model_data.get('feature_columns', 
                                                   ['amount', 'card_present', 'hour_of_day', 'day_of_week'])
            self.trained_at = model_data.get('trained_at', 'Unknown')
            
            self.initialized = True
            logger.info(f"Model loaded successfully from {model_path}")
            logger.info(f"Model was trained at: {self.trained_at}")
            logger.info(f"Feature columns: {self.feature_columns}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
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
                hour_of_day = 12
                day_of_week = 1
        else:
            hour_of_day = 12
            day_of_week = 1
            
        # Prepare feature vector
        features = [
            transaction.get('amount', 0),
            1 if transaction.get('card_present', True) else 0,
            hour_of_day,
            day_of_week
        ]
        
        return np.array(features).reshape(1, -1)
    
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
        """
        if not self.initialized:
            logger.warning("Model not initialized. Returning default prediction.")
            return {
                'is_fraud': False,
                'fraud_probability': 0.0,
                'confidence': 0.0,
                'error': 'Model not loaded'
            }
            
        try:
            # Extract features
            features = self._extract_features(transaction)
            
            # Scale features
            features_scaled = self.scaler.transform(features)
            
            # Predict
            prediction = self.model.predict(features_scaled)[0]
            probabilities = self.model.predict_proba(features_scaled)[0]
            
            # Get fraud probability
            fraud_prob = float(probabilities[1])
            normal_prob = float(probabilities[0])
            
            # Determine if fraudulent
            is_fraud = bool(prediction) or fraud_prob > 0.5
            
            result = {
                'is_fraud': is_fraud,
                'fraud_probability': fraud_prob,
                'normal_probability': normal_prob,
                'confidence': max(fraud_prob, normal_prob),
                'model_prediction': int(prediction)
            }
            
            # Log high-risk transactions
            if is_fraud:
                logger.warning(
                    f"POTENTIAL FRAUD DETECTED: {transaction.get('transaction_id', 'UNKNOWN')} - "
                    f"Amount: ${transaction.get('amount', 0):.2f}, "
                    f"Probability: {fraud_prob:.2%}"
                )
                
            return result
            
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {
                'is_fraud': False,
                'fraud_probability': 0.0,
                'confidence': 0.0,
                'error': str(e)
            }
    
    def analyze_transaction(self, transaction: Dict) -> Dict:
        """
        Perform comprehensive analysis on a transaction.
        
        Args:
            transaction: Transaction dictionary
            
        Returns:
            Dictionary with transaction details and fraud analysis
        """
        # Get ML prediction
        prediction = self.predict(transaction)
        
        # Add rule-based fraud indicators
        indicators = []
        
        # High amount check
        if transaction.get('amount', 0) > 5000:
            indicators.append({
                'type': 'HIGH_AMOUNT',
                'severity': 'HIGH',
                'description': f"Transaction amount ${transaction.get('amount', 0):.2f} exceeds $5000"
            })
            
        # Card not present check
        if not transaction.get('card_present', True):
            indicators.append({
                'type': 'CARD_NOT_PRESENT',
                'severity': 'MEDIUM',
                'description': "Card was not physically present"
            })
            
        # Unusual time check (late night/early morning)
        try:
            timestamp_str = transaction.get('timestamp', '')
            if timestamp_str:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                if dt.hour < 6 or dt.hour > 22:
                    indicators.append({
                        'type': 'UNUSUAL_TIME',
                        'severity': 'LOW',
                        'description': f"Transaction at unusual hour: {dt.hour}:00"
                    })
        except:
            pass
            
        # Combine results
        analysis = {
            'transaction_id': transaction.get('transaction_id'),
            'user_id': transaction.get('user_id'),
            'amount': transaction.get('amount'),
            'timestamp': transaction.get('timestamp'),
            **prediction,
            'indicators': indicators,
            'risk_level': self._calculate_risk_level(prediction, indicators)
        }
        
        return analysis
    
    def _calculate_risk_level(self, prediction: Dict, indicators: list) -> str:
        """
        Calculate overall risk level.
        
        Args:
            prediction: ML prediction results
            indicators: List of fraud indicators
            
        Returns:
            Risk level: LOW, MEDIUM, HIGH, or CRITICAL
        """
        # Check ML prediction
        if prediction.get('fraud_probability', 0) > 0.8:
            return 'CRITICAL'
            
        # Count high severity indicators
        high_severity = sum(1 for i in indicators if i.get('severity') == 'HIGH')
        if high_severity > 0:
            return 'HIGH'
            
        # Check medium severity
        medium_severity = sum(1 for i in indicators if i.get('severity') == 'MEDIUM')
        if medium_severity > 1:
            return 'HIGH'
        elif medium_severity > 0:
            return 'MEDIUM'
            
        # Check ML probability
        if prediction.get('fraud_probability', 0) > 0.5:
            return 'MEDIUM'
            
        return 'LOW'


# Example usage
if __name__ == "__main__":
    # Test with sample transactions
    detector = FraudDetector()
    
    # Test transaction (normal)
    normal_txn = {
        'transaction_id': 'TXN_TEST_001',
        'user_id': 'USER001',
        'amount': 50.00,
        'location': 'New York, USA',
        'card_present': True,
        'timestamp': datetime.now().isoformat()
    }
    
    print("Normal Transaction Analysis:")
    result = detector.analyze_transaction(normal_txn)
    print(result)
    print()
    
    # Test transaction (suspicious)
    suspicious_txn = {
        'transaction_id': 'TXN_TEST_002',
        'user_id': 'USER002',
        'amount': 9500.00,
        'location': 'Unknown',
        'card_present': False,
        'timestamp': datetime.now().isoformat()
    }
    
    print("Suspicious Transaction Analysis:")
    result = detector.analyze_transaction(suspicious_txn)
    print(result)

