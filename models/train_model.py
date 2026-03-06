"""
Machine Learning Model Training Script
Trains a Logistic Regression model to detect fraudulent transactions
"""

import os
import pandas as pd
import numpy as np
import pickle
import logging
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (classification_report, confusion_matrix, 
                            accuracy_score, precision_score, recall_score, f1_score)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_sample_data(output_path: str = None, num_samples: int = 10000):
    """
    Generate synthetic training data for fraud detection.
    
    Args:
        output_path: Path to save CSV file
        num_samples: Number of samples to generate
        
    Returns:
        DataFrame with training data
    """
    logger.info(f"Generating {num_samples} sample transactions...")
    
    np.random.seed(42)
    
    # Transaction data
    data = {
        'transaction_id': [f'TXN{i:08d}' for i in range(num_samples)],
        'user_id': [f'USER{np.random.randint(1, 101):03d}' for _ in range(num_samples)],
        'amount': [],
        'location': [],
        'merchant': [],
        'card_present': [],
        'hour_of_day': [],
        'day_of_week': []
    }
    
    # Generate locations
    locations = [
        "New York, USA", "Los Angeles, USA", "Chicago, USA", "Houston, USA",
        "Phoenix, USA", "London, UK", "Paris, France", "Berlin, Germany",
        "Tokyo, Japan", "Sydney, Australia"
    ]
    
    # Generate merchants
    merchants = [
        "Amazon", "Walmart", "Target", "Best Buy", "Apple Store",
        "Starbucks", "McDonalds", "Netflix", "Spotify", "Uber"
    ]
    
    # Generate transactions with realistic distribution
    for i in range(num_samples):
        # 80% normal transactions (small amounts), 20% potentially suspicious
        if np.random.random() < 0.8:
            # Normal transaction
            amount = np.random.uniform(1.0, 500.0)
            card_present = True
        else:
            # Potentially suspicious - higher amount, sometimes card not present
            amount = np.random.uniform(500.0, 10000.0)
            card_present = np.random.choice([True, False], p=[0.7, 0.3])
        
        data['amount'].append(round(amount, 2))
        data['card_present'].append(card_present)
        data['location'].append(np.random.choice(locations))
        data['merchant'].append(np.random.choice(merchants))
        data['hour_of_day'].append(np.random.randint(0, 24))
        data['day_of_week'].append(np.random.randint(1, 8))
    
    df = pd.DataFrame(data)
    
    # Create labels based on rules (ground truth)
    df['is_fraud'] = (
        (df['amount'] > 5000) |
        ((~df['card_present']) & (df['amount'] > 1000)) |
        (df['amount'] > 8000)
    ).astype(int)
    
    # Save to CSV if path provided
    if output_path:
        df.to_csv(output_path, index=False)
        logger.info(f"Training data saved to {output_path}")
    
    # Print statistics
    fraud_count = df['is_fraud'].sum()
    logger.info(f"Generated {num_samples} transactions")
    logger.info(f"  Normal: {num_samples - fraud_count} ({100*(num_samples-fraud_count)/num_samples:.1f}%)")
    logger.info(f"  Fraud: {fraud_count} ({100*fraud_count/num_samples:.1f}%)")
    
    return df


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
        self.label_encoder_locations = LabelEncoder()
        
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
        
        # Encode card_present as integer
        data['card_present'] = data['card_present'].astype(int)
        
        # Encode locations
        data['location_encoded'] = self.label_encoder_locations.fit_transform(data['location'])
        
        # Select features for training
        feature_cols = self.feature_columns.copy()
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
        logger.info(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")
        logger.info(f"Precision: {precision_score(y_test, y_pred):.4f}")
        logger.info(f"Recall: {recall_score(y_test, y_pred):.4f}")
        logger.info(f"F1 Score: {f1_score(y_test, y_pred):.4f}")
        logger.info(f"\nConfusion Matrix:\n{confusion_matrix(y_test, y_pred)}")
        logger.info(f"\nClassification Report:\n{classification_report(y_test, y_pred)}")
        
        return X_train, X_test, y_train, y_test
    
    def predict(self, features: np.ndarray) -> dict:
        """
        Predict fraud for transaction features.
        
        Args:
            features: Feature array [amount, card_present, hour, day, location_encoded]
            
        Returns:
            Dictionary with prediction and probability
        """
        if self.model is None:
            raise ValueError("Model not trained yet!")
        
        # Scale features
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        # Predict
        prediction = self.model.predict(features_scaled)[0]
        probability = self.model.predict_proba(features_scaled)[0]
        
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
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'label_encoder_locations': self.label_encoder_locations,
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
        self.label_encoder_locations = model_data.get('label_encoder_locations')
        self.feature_columns = model_data.get('feature_columns', self.feature_columns)
        
        logger.info(f"Model loaded from {filepath}")


def main():
    """Main function to train and save the model"""
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, 'sample_data.csv')
    model_path = os.path.join(script_dir, 'fraud_model.pkl')
    
    # Generate sample data if it doesn't exist
    if not os.path.exists(data_path):
        logger.info("Generating sample training data...")
        df = generate_sample_data(data_path, num_samples=10000)
    else:
        logger.info("Loading existing training data...")
        df = pd.read_csv(data_path)
    
    # Initialize model
    fraud_model = FraudDetectionModel()
    
    # Preprocess data
    X, y = fraud_model.preprocess_data(df)
    
    # Train model
    fraud_model.train(X, y)
    
    # Save model
    fraud_model.save_model(model_path)
    
    logger.info("\n" + "="*50)
    logger.info("MODEL TRAINING COMPLETE!")
    logger.info("="*50)
    logger.info(f"Model saved to: {model_path}")
    logger.info("You can now use this model for fraud detection.")
    
    # Test prediction
    test_features = np.array([5000, 0, 14, 1, 5])  # amount, card_not_present, hour, day, location
    result = fraud_model.predict(test_features)
    logger.info(f"\nTest prediction: {result}")


if __name__ == "__main__":
    main()

