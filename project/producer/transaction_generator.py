"""
Transaction Generator Module
Generates random bank transactions for simulation purposes
"""

import random
import uuid
from datetime import datetime, timedelta
from typing import Dict, List
import config


class TransactionGenerator:
    """
    Generates random bank transactions with realistic data patterns.
    Used to simulate incoming bank transaction stream.
    """
    
    def __init__(self):
        self.locations = config.LOCATIONS
        self.merchants = config.MERCHANTS
        self.user_ids = [f"USER{str(i).zfill(3)}" for i in range(1, 101)]
        
    def generate_transaction_id(self) -> str:
        """Generate unique transaction ID"""
        return f"TXN{uuid.uuid4().hex[:12].upper()}"
    
    def generate_user_id(self) -> str:
        """Generate random user ID"""
        return random.choice(self.user_ids)
    
    def generate_amount(self) -> float:
        """
        Generate random transaction amount.
        Most transactions are small, some are large (potential fraud)
        """
        # 80% normal transactions (small amounts), 20% large amounts
        if random.random() < 0.8:
            return round(random.uniform(1.0, 500.0), 2)
        else:
            return round(random.uniform(500.0, config.MAX_TRANSACTION_AMOUNT), 2)
    
    def generate_location(self) -> str:
        """Generate random transaction location"""
        return random.choice(self.locations)
    
    def generate_merchant(self) -> str:
        """Generate random merchant name"""
        return random.choice(self.merchants)
    
    def generate_timestamp(self) -> str:
        """Generate current timestamp"""
        return datetime.now().isoformat()
    
    def generate_card_present(self) -> bool:
        """Generate card presence indicator"""
        return random.choice([True, True, True, False])  # 75% card present
    
    def generate_transaction(self) -> Dict:
        """
        Generate a complete random bank transaction.
        
        Returns:
            Dict: Transaction data with fields:
                - transaction_id: Unique identifier
                - user_id: User identifier
                - amount: Transaction amount
                - location: Transaction location
                - timestamp: Transaction time
                - merchant: Merchant name
                - card_present: Whether card was physically present
        """
        return {
            'transaction_id': self.generate_transaction_id(),
            'user_id': self.generate_user_id(),
            'amount': self.generate_amount(),
            'location': self.generate_location(),
            'timestamp': self.generate_timestamp(),
            'merchant': self.generate_merchant(),
            'card_present': self.generate_card_present()
        }
    
    def generate_batch(self, count: int = 10) -> List[Dict]:
        """
        Generate a batch of transactions.
        
        Args:
            count: Number of transactions to generate
            
        Returns:
            List[Dict]: List of transaction dictionaries
        """
        return [self.generate_transaction() for _ in range(count)]


# Example usage
if __name__ == "__main__":
    generator = TransactionGenerator()
    
    # Generate single transaction
    transaction = generator.generate_transaction()
    print("Single Transaction:")
    print(transaction)
    print()
    
    # Generate batch of transactions
    batch = generator.generate_batch(5)
    print("Batch of Transactions:")
    for txn in batch:
        print(txn)

