"""
Machine Learning Model Training Script
Trains a Logistic Regression model to detect fraudulent transactions
"""

import pandas as pd
import numpy as np
import pickle
import logging
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FraudDetectionModel:
    """
    Machine learning model for detecting fraudulent bank transactions.
    Uses Logistic Regression for classification.
    """
    
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoders = {}
        self.feature_columns = ['amount', 'card_present', 'hour_of_day', 'day_of_week']
        
    def load_training_data(self, filepath: str) -> pd.DataFrame:
        """
        Load training data from CSV file.
        
        Args:
            filepath: Path to CSV file
            
        Returns:
            DataFrame with training data
        """
        logger.info(f"Loading training data from {filepath}")
        df = pd.read_csv(filepath)
        logger.info(f"Loaded {len(df)} records")
        logger.info(f"Columns: {df.columns.tolist()}")
        return df
    
    def preprocess_data(self, df: pd.DataFrame) -> tuple:
        """
        Preprocess the training data.
        
        Args:
            df: Raw DataFrame
            
        Returns:
            Tuple of (X, y) - features and labels
        """
        logger.info("Preprocessing data...")
        
        # Create a copy to avoid modifying original
        data = df.copy()
        
        # Encode categorical features
        categorical_columns = ['location']
        for col in categorical_columns:
            if col in data.columns:
                if col not in self.label_encoders:
                    self.label_encoders[col] = LabelEncoder()
                    data[col + '_encoded'] = self.label_encoders[col].fit_transform(data[col])
                else:
                    data[col + '_encoded'] = self.label_encoders[col].transform(data[col])
                    
        # Select features for training
        feature_cols = self.feature_columns.copy()
        if 'location_encoded' in data.columns:
            feature_cols.append('location_encoded')
            
        # Handle missing values
        data = data.fillna(0)
        
        # Extract features and target
        X = data[feature_cols].values
        y = data['is_fraud'].values
        
        logger.info(f"Feature columns: {feature_cols}")
        logger.info(f"X shape: {X.shape}, y shape: {y.shape}")
        
        return X, y
    
    def train(self, X: np.ndarray, y: np.ndarray, test_size: float = 0.2):
        """
        Train the fraud detection model.
        
        Args:
            X: Feature matrix
            y: Target labels
            test_size: Fraction for test split
        """
        logger.info("Splitting data into train/test sets...")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        logger.info(f"Training set: {len(X_train)} samples")
        logger.info(f"Test set: {len(X_test)} samples")
        
        # Scale features
        logger.info("Scaling features...")
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train model
        logger.info("Training Logistic Regression model...")
        self.model = LogisticRegression(
            random_state=42,
            max_iter=1000,
            class_weight='balanced',  # Handle imbalanced classes
            solver='lbfgs'
        )
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        
        logger.info("\n" + "="*50)
        logger.info("MODEL EVALUATION RESULTS")
        logger.info("="*50)
        logger.info(f"\nAccuracy: {accuracy_score(y_test, y_pred):.4f}")
        logger.info(f"\nConfusion Matrix:\n{confusion_matrix(y_test, y_pred)}")
        logger.info(f"\nClassification Report:\n{classification_report(y_test, y_pred)}")
        
        return X_train, X_test, y_train, y_test
    
    def predict(self, features: dict) -> dict:
        """
        Predict fraud for a single transaction.
        
        Args:
            features: Dictionary of transaction features
            
        Returns:
            Dictionary with prediction and probability
        """
        # Prepare features
        feature_vector = np.array([
            features.get('amount', 0),
            1 if features.get('card_present', True) else 0,
            features.get('hour_of_day', 12),
            features.get('day_of_week', 1)
        ]).reshape(1, -1)
        
        # Scale features
        feature_vector_scaled = self.scaler.transform(feature_vector)
        
        # Predict
        prediction = self.model.predict(feature_vector_scaled)[0]
        probability = self.model.predict_proba(feature_vector_scaled)[0]
        
        return {
            'is_fraud': bool(prediction),
            'fraud_probability': float(probability[1]),
            'normal_probability': float(probability[0])
        }
    
    def save_model(self, filepath: str):
        """
        Save the trained model to disk.
        
        Args:
            filepath: Path to save the model
        """
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'label_encoders': self.label_encoders,
            'feature_columns': self.feature_columns,
            'trained_at': datetime.now().isoformat()
        }
        
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)
            
        logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str):
        """
        Load a trained model from disk.
        
        Args:
            filepath: Path to the model file
        """
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
            
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.label_encoders = model_data.get('label_encoders', {})
        self.feature_columns = model_data.get('feature_columns', self.feature_columns)
        
        logger.info(f"Model loaded from {filepath}")


def main():
    """Main function to train and save the model"""
    
    # Initialize model
    fraud_model = FraudDetectionModel()
    
    # Load training data
    data_path = 'sample_data.csv'
    df = fraud_model.load_training_data(data_path)
    
    # Preprocess data
    X, y = fraud_model.preprocess_data(df)
    
    # Train model
    fraud_model.train(X, y)
    
    # Save model
    model_path = 'model.pkl'
    fraud_model.save_model(model_path)
    
    logger.info("Model training complete!")
    
    # Test prediction
    test_transaction = {
        'amount': 5000,
        'card_present': False,
        'hour_of_day': 3,
        'day_of_week': 1
    }
    
    result = fraud_model.predict(test_transaction)
    logger.info(f"\nTest prediction: {result}")


if __name__ == "__main__":
    main()

