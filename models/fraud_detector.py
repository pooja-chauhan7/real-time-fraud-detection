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
        self.model = None
        self.scaler = None
        self.model_path = model_path
        self.initialized = False
        self.feature_columns = ['amount', 'card_present', 'hour_of_day', 'day_of_week']
        
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
    
    def load_model(self, model_path: str):
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
                
            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_columns = model_data.get('feature_columns', self.feature_columns)
            self.trained_at = model_data.get('trained_at', 'Unknown')
            
            self.initialized = True
            logger.info(f"ML Model loaded successfully from {model_path}")
            
        except Exception as e:
            logger.warning(f"Failed to load ML model: {e}. Using rule-based detection.")
            self.initialized = False
    
    def _extract_features(self, transaction: Dict) -> np.ndarray:
        timestamp_str = transaction.get('timestamp', '')
        if timestamp_str:
            try:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                hour_of_day = dt.hour
                day_of_week = dt.weekday() + 1
            except:
                hour_of_day = datetime.now().hour
                day_of_week = datetime.now().weekday() + 1
        else:
            hour_of_day = datetime.now().hour
            day_of_week = datetime.now().weekday() + 1
            
        features = [
            float(transaction.get('amount', 0)),
            1 if transaction.get('card_present', True) else 0,
            float(hour_of_day),
            float(day_of_week)
        ]
        
        return np.array(features).reshape(1, -1)
    
    def _rule_based_detection(self, transaction: Dict) -> Dict:
        is_fraud = False
        reasons = []
        fraud_probability = 0.0
        
        amount = transaction.get('amount', 0)
        card_present = transaction.get('card_present', True)
        location_changed = transaction.get('location_changed', False)
        
        # Rule 1: High amount check (>= ₹50,000) - PRIMARY FRAUD INDICATOR
        if amount >= 50000:
            is_fraud = True
            reasons.append(f"High amount: ₹{amount:,.2f} (>= ₹50,000)")
            fraud_probability = max(fraud_probability, 0.9)
        
        # Rule 2: Very high amount (> ₹100,000) - CRITICAL
        if amount > 100000:
            is_fraud = True
            reasons.append(f"Critical amount: ₹{amount:,.2f} (>= ₹100,000)")
            fraud_probability = 0.98
        
        # Rule 3: Sudden location change - Major fraud indicator
        if location_changed:
            is_fraud = True
            prev_loc = transaction.get('previous_location', 'Unknown')
            curr_loc = transaction.get('location', 'Unknown')
            reasons.append(f"Location changed suddenly: {prev_loc} -> {curr_loc}")
            fraud_probability = max(fraud_probability, 0.8)
        
        # Rule 4: Card not present + high amount (>= ₹25,000)
        if not card_present and amount >= 25000:
            is_fraud = True
            reasons.append(f"Card not present for high amount: ₹{amount:,.2f}")
            fraud_probability = max(fraud_probability, 0.75)
        
        # Rule 5: Multiple rapid transactions - checked via transaction history
        rapid_transactions = transaction.get('rapid_transactions', 0)
        if rapid_transactions >= 3:
            is_fraud = True
            reasons.append(f"Multiple rapid transactions: {rapid_transactions} in few seconds")
            fraud_probability = max(fraud_probability, 0.85)
        
        # Rule 6: Suspicious pattern detected from bank statement
        suspicious_pattern = transaction.get('suspicious_pattern', False)
        if suspicious_pattern:
            is_fraud = True
            reasons.append("Suspicious bank statement pattern detected")
            fraud_probability = max(fraud_probability, 0.8)
        
        # Rule 7: Unusual time (late night) + high amount
        try:
            timestamp_str = transaction.get('timestamp', '')
            if timestamp_str and amount >= 25000:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                if dt.hour < 5 or dt.hour > 23:
                    reasons.append("High-value transaction at unusual hour")
                    fraud_probability = max(fraud_probability, 0.4)
        except:
            pass
        
        return {
            'is_fraud': is_fraud,
            'fraud_probability': min(fraud_probability, 1.0),
            'reasons': reasons,
            'method': 'rule_based'
        }
    
    def predict(self, transaction: Dict) -> Dict:
        rule_result = self._rule_based_detection(transaction)
        
        if self.initialized and self.model is not None:
            try:
                features = self._extract_features(transaction)
                features_scaled = self.scaler.transform(features)
                
                ml_prediction = self.model.predict(features_scaled)[0]
                ml_probability = self.model.predict_proba(features_scaled)[0]
                
                ml_fraud_prob = float(ml_probability[1])
                combined_probability = (0.6 * ml_fraud_prob) + (0.4 * rule_result['fraud_probability'])
                
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
            result = rule_result
        
        result['risk_level'] = self._calculate_risk_level(result['fraud_probability'])
        
        if result['is_fraud']:
            logger.warning(
                f"FRAUD DETECTED: {transaction.get('transaction_id', 'UNKNOWN')} - "
                f"Amount: ${transaction.get('amount', 0):.2f}, "
                f"Probability: {result['fraud_probability']:.2%}, "
                f"Reasons: {', '.join(result['reasons'])}"
            )
        
        return result
    
    def analyze_transaction(self, transaction: Dict) -> Dict:
        prediction = self.predict(transaction)
        
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
        if fraud_probability >= 0.8:
            return 'CRITICAL'
        elif fraud_probability >= 0.6:
            return 'HIGH'
        elif fraud_probability >= 0.4:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def batch_predict(self, transactions: List[Dict]) -> List[Dict]:
        return [self.analyze_transaction(txn) for txn in transactions]


def create_fraud_detector(model_path: str = None) -> FraudDetector:
    return FraudDetector(model_path=model_path)


if __name__ == "__main__":
    detector = FraudDetector()
    
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
    print()
    
    suspicious_txn = {
        'transaction_id': 'TXN_TEST_002',
        'user_id': 'USER002',
        'amount': 75000.00,
        'location': 'Tokyo, Japan',
        'merchant': 'Unknown',
        'card_present': False,
        'timestamp': datetime.now().isoformat(),
        'location_changed': True,
        'previous_location': 'New York, USA'
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

