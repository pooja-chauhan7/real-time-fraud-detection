"""
Flask Backend API
REST API for fraud detection system
Serves transaction data and fraud alerts to frontend dashboard
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# MongoDB connection
mongo_client = None
db = None


def init_db():
    """Initialize MongoDB connection"""
    global mongo_client, db
    
    try:
        mongo_uri = config.get_mongo_uri()
        mongo_client = MongoClient(mongo_uri)
        db = mongo_client[config.MONGO_DB]
        
        # Create indexes
        db.transactions.create_index("transaction_id", unique=True)
        db.transactions.create_index("timestamp")
        db.transactions.create_index("is_fraud")
        db.alerts.create_index("transaction_id")
        
        logger.info(f"Connected to MongoDB: {config.MONGO_DB}")
    except Exception as e:
        logger.warning(f"MongoDB connection failed: {e}. Using in-memory storage.")
        mongo_client = None
        db = None


# In-memory storage for prototype (fallback)
in_memory_transactions = []
in_memory_alerts = []


# ==================== API Routes ====================

@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({
        'status': 'running',
        'service': 'Fraud Detection API',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    """
    Get all transactions with optional filters
    Query params: limit, offset, fraud_only
    """
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        fraud_only = request.args.get('fraud_only', 'false').lower() == 'true'
        
        if db:
            # Query from MongoDB
            query = {"is_fraud": True} if fraud_only else {}
            transactions = list(db.transactions
                .find(query)
                .sort("timestamp", -1)
                .skip(offset)
                .limit(limit))
            
            # Convert ObjectId to string
            for t in transactions:
                if '_id' in t:
                    t['_id'] = str(t['_id'])
        else:
            # Use in-memory storage
            transactions = in_memory_transactions
            if fraud_only:
                transactions = [t for t in transactions if t.get('is_fraud')]
            transactions = transactions[offset:offset+limit]
        
        return jsonify({
            'success': True,
            'count': len(transactions),
            'transactions': transactions
        })
        
    except Exception as e:
        logger.error(f"Error getting transactions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/transactions/<transaction_id>', methods=['GET'])
def get_transaction(transaction_id):
    """Get a specific transaction by ID"""
    try:
        if db:
            transaction = db.transactions.find_one({"transaction_id": transaction_id})
            if transaction:
                transaction['_id'] = str(transaction['_id'])
        else:
            transaction = next(
                (t for t in in_memory_transactions 
                 if t.get('transaction_id') == transaction_id),
                None
            )
        
        if transaction:
            return jsonify({'success': True, 'transaction': transaction})
        else:
            return jsonify({'success': False, 'error': 'Transaction not found'}), 404
            
    except Exception as e:
        logger.error(f"Error getting transaction: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/transactions', methods=['POST'])
def add_transaction():
    """Add a new transaction"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Add timestamp if not provided
        if 'timestamp' not in data:
            data['timestamp'] = datetime.now().isoformat()
        
        # Set default fraud status
        if 'is_fraud' not in data:
            data['is_fraud'] = False
        
        if db:
            result = db.transactions.insert_one(data)
            data['_id'] = str(result.inserted_id)
        else:
            in_memory_transactions.append(data)
        
        # Create alert if fraud detected
        if data.get('is_fraud'):
            alert = {
                'transaction_id': data.get('transaction_id'),
                'user_id': data.get('user_id'),
                'amount': data.get('amount'),
                'timestamp': data.get('timestamp'),
                'alert_time': datetime.now().isoformat(),
                'status': 'new'
            }
            
            if db:
                db.alerts.insert_one(alert)
            else:
                in_memory_alerts.append(alert)
        
        return jsonify({'success': True, 'transaction': data}), 201
        
    except Exception as e:
        logger.error(f"Error adding transaction: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """
    Get all fraud alerts
    Query params: limit, status
    """
    try:
        limit = int(request.args.get('limit', 50))
        status = request.args.get('status')
        
        if db:
            query = {"status": status} if status else {}
            alerts = list(db.alerts
                .find(query)
                .sort("alert_time", -1)
                .limit(limit))
            
            for a in alerts:
                if '_id' in a:
                    a['_id'] = str(a['_id'])
        else:
            alerts = in_memory_alerts
            if status:
                alerts = [a for a in alerts if a.get('status') == status]
            alerts = alerts[:limit]
        
        return jsonify({
            'success': True,
            'count': len(alerts),
            'alerts': alerts
        })
        
    except Exception as e:
        logger.error(f"Error getting alerts: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/alerts/<transaction_id>', methods=['PUT'])
def update_alert(transaction_id):
    """Update alert status (acknowledge, resolve)"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'success': False, 'error': 'Status not provided'}), 400
        
        if db:
            result = db.alerts.update_one(
                {"transaction_id": transaction_id},
                {"$set": {"status": new_status, "updated_at": datetime.now().isoformat()}}
            )
            
            if result.modified_count == 0:
                return jsonify({'success': False, 'error': 'Alert not found'}), 404
        else:
            for alert in in_memory_alerts:
                if alert.get('transaction_id') == transaction_id:
                    alert['status'] = new_status
                    alert['updated_at'] = datetime.now().isoformat()
                    break
            else:
                return jsonify({'success': False, 'error': 'Alert not found'}), 404
        
        return jsonify({'success': True, 'status': new_status})
        
    except Exception as e:
        logger.error(f"Error updating alert: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get transaction statistics"""
    try:
        if db:
            total = db.transactions.count_documents({})
            fraud_count = db.transactions.count_documents({"is_fraud": True})
            alerts_count = db.alerts.count_documents({})
            new_alerts = db.alerts.count_documents({"status": "new"})
            
            # Calculate total amount
            pipeline = [
                {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
            ]
            amount_result = list(db.transactions.aggregate(pipeline))
            total_amount = amount_result[0]['total'] if amount_result else 0
        else:
            total = len(in_memory_transactions)
            fraud_count = sum(1 for t in in_memory_transactions if t.get('is_fraud'))
            alerts_count = len(in_memory_alerts)
            new_alerts = sum(1 for a in in_memory_alerts if a.get('status') == 'new')
            total_amount = sum(t.get('amount', 0) for t in in_memory_transactions)
        
        return jsonify({
            'success': True,
            'stats': {
                'total_transactions': total,
                'fraud_transactions': fraud_count,
                'fraud_percentage': round(fraud_count / total * 100, 2) if total > 0 else 0,
                'total_amount': round(total_amount, 2),
                'total_alerts': alerts_count,
                'new_alerts': new_alerts,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/recent-transactions', methods=['GET'])
def get_recent_transactions():
    """Get recent transactions for real-time dashboard"""
    try:
        limit = int(request.args.get('limit', 20))
        
        if db:
            transactions = list(db.transactions
                .find()
                .sort("timestamp", -1)
                .limit(limit))
            
            for t in transactions:
                if '_id' in t:
                    t['_id'] = str(t['_id'])
        else:
            transactions = in_memory_transactions[-limit:]
        
        return jsonify({
            'success': True,
            'transactions': transactions
        })
        
    except Exception as e:
        logger.error(f"Error getting recent transactions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ==================== Main ====================

def main():
    """Run the Flask application"""
    # Initialize database
    init_db()
    
    # Run Flask app
    logger.info(f"Starting Flask API on {config.API_HOST}:{config.API_PORT}")
    app.run(
        host=config.API_HOST,
        port=config.API_PORT,
        debug=config.API_DEBUG
    )


if __name__ == "__main__":
    main()

