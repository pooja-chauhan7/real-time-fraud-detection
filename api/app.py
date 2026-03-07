"""
Real-Time Fraud Detection System - Backend API
================================================
A professional Flask API for fraud detection with SQLite database.
Fixed: Stable real-time updates, proper fraud detection, database integration.
"""

import os
import sys
import logging
import uuid
import hashlib
import threading
import time
import random
import sqlite3
import csv
import io
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, jsonify, request, session, g, send_file
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database path
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fraud_detection.db')

# Global state for stream
stream_running = False
stream_thread = None
last_stats_update = None

# Configuration
FRAUD_AMOUNT_THRESHOLD = 50000  # Amount > 50,000 is suspicious
RAPID_TRANSACTION_COUNT = 3  # More than 3 transactions in window
RAPID_TRANSACTION_WINDOW = 10  # seconds
LOCATION_CHANGE_WEIGHT = 0.3
HIGH_AMOUNT_WEIGHT = 0.4
RISK_WEIGHT_DUPLICATE = 0.35
UNKNOWN_LOCATION_WEIGHT = 0.25

# Demo configuration
DEMO_LOCATIONS = [
    "New York, USA", "Los Angeles, USA", "Chicago, USA", "Houston, USA",
    "Phoenix, USA", "London, UK", "Paris, France", "Berlin, Germany",
    "Tokyo, Japan", "Sydney, Australia", "Toronto, Canada", "Mumbai, India",
    "Dubai, UAE", "Singapore", "Hong Kong", "Seoul, South Korea"
]

DEMO_MERCHANTS = [
    "Amazon", "Walmart", "Target", "Best Buy", "Apple Store",
    "Starbucks", "McDonalds", "Netflix", "Spotify", "Uber",
    "Airbnb", "DoorDash", "Google Pay", "PayPal", "Venmo"
]

USER_IDS = [f"USER{str(i).zfill(3)}" for i in range(1, 21)]


def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()


def generate_transaction_id():
    """Generate unique transaction ID"""
    return f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"


def generate_otp():
    """Generate 6-digit OTP"""
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])


def get_db():
    """Get database connection"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


def close_connection(exception):
    """Close database connection"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_database():
    """Initialize database with all required tables"""
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    
    # Users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE NOT NULL,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT,
        mobile_number TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_verified INTEGER DEFAULT 0)''')
    
    # Verified users table
    cursor.execute('''CREATE TABLE IF NOT EXISTS verified_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE NOT NULL,
        username TEXT NOT NULL,
        email TEXT,
        mobile_number TEXT NOT NULL,
        verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # OTP store table
    cursor.execute('''CREATE TABLE IF NOT EXISTS otp_store (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mobile_number TEXT NOT NULL,
        otp_code TEXT NOT NULL,
        user_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        verified INTEGER DEFAULT 0)''')
    
    # Transactions table
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id TEXT UNIQUE NOT NULL,
        user_id TEXT NOT NULL,
        amount REAL NOT NULL,
        transaction_type TEXT DEFAULT 'TRANSFER',
        receiver_account TEXT,
        location TEXT,
        latitude REAL,
        longitude REAL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_fraud INTEGER DEFAULT 0,
        fraud_reason TEXT,
        risk_level TEXT DEFAULT 'LOW',
        fraud_probability REAL DEFAULT 0.0,
        merchant TEXT,
        description TEXT,
        card_present INTEGER DEFAULT 1)''')
    
    # Alerts table
    cursor.execute('''CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_id TEXT UNIQUE NOT NULL,
        transaction_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        amount REAL NOT NULL,
        alert_type TEXT DEFAULT 'FRAUD_DETECTED',
        alert_message TEXT,
        risk_level TEXT DEFAULT 'HIGH',
        status TEXT DEFAULT 'new',
        alert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        acknowledged_at TIMESTAMP)''')
    
    # Bank statements table
    cursor.execute('''CREATE TABLE IF NOT EXISTS bank_statements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        statement_id TEXT UNIQUE NOT NULL,
        user_id TEXT NOT NULL,
        filename TEXT NOT NULL,
        total_transactions INTEGER DEFAULT 0,
        total_amount REAL DEFAULT 0,
        suspicious_count INTEGER DEFAULT 0,
        analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending')''')
    
    # Activity logs table
    cursor.execute('''CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        activity_type TEXT NOT NULL,
        description TEXT,
        ip_address TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Create indexes
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_is_fraud ON transactions(is_fraud)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_alerts_alert_time ON alerts(alert_time)')
    
    db.commit()
    db.close()
    logger.info("Database initialized successfully")


# ==================== FRAUD DETECTION LOGIC ====================

def detect_fraud(transaction_data):
    """
    Detect if transaction is fraudulent based on rules:
    1. Amount > 50,000
    2. Multiple transactions within few seconds
    3. Sudden location change
    4. Unknown location
    """
    fraud_indicators = []
    is_fraud = False
    risk_level = 'LOW'
    fraud_probability = 0.0
    
    user_id = transaction_data.get('user_id')
    amount = float(transaction_data.get('amount', 0))
    location = transaction_data.get('location', '')
    timestamp = transaction_data.get('timestamp', datetime.now().isoformat())
    
    try:
        db = get_db()
        cursor = db.cursor()
        
        # Check 1: Amount threshold (HIGH RISK - automatically fraud)
        if amount > FRAUD_AMOUNT_THRESHOLD:
            is_fraud = True
            fraud_indicators.append(f"High amount: ₹{amount:,} exceeds threshold of ₹{FRAUD_AMOUNT_THRESHOLD:,}")
            risk_level = 'HIGH'
            fraud_probability = max(fraud_probability, 0.85)
        
        # Check 2: Rapid transactions (multiple within seconds)
        cursor.execute("""
            SELECT COUNT(*) as count, MAX(timestamp) as last_txn
            FROM transactions 
            WHERE user_id = ? AND timestamp > datetime('now', '-10 seconds')
        """, (user_id,))
        
        result = cursor.fetchone()
        if result and result['count'] >= RAPID_TRANSACTION_COUNT:
            is_fraud = True
            fraud_indicators.append(f"Multiple rapid transactions detected ({result['count']} in last 10 seconds)")
            risk_level = 'HIGH'
            fraud_probability = max(fraud_probability, 0.90)
        
        # Check 3: Location change detection
        cursor.execute("""
            SELECT location, timestamp 
            FROM transactions 
            WHERE user_id = ? AND location IS NOT NULL
            ORDER BY timestamp DESC LIMIT 1
        """, (user_id,))
        
        last_txn = cursor.fetchone()
        if last_txn and location != last_txn['location'] and location:
            # Check if location is "unknown" or "unusual"
            if 'unknown' in location.lower() or 'test' in location.lower():
                is_fraud = True
                fraud_indicators.append(f"Transaction from unknown location: {location}")
                risk_level = 'HIGH'
                fraud_probability = max(fraud_probability, 0.80)
            else:
                fraud_indicators.append(f"Location changed from {last_txn['location']} to {location}")
                fraud_probability = max(fraud_probability, 0.40)
                if not is_fraud and fraud_probability > 0.3:
                    risk_level = 'MEDIUM'
        
        # Check 4: Very high risk score from probability
        if not is_fraud and fraud_probability >= 0.5:
            is_fraud = True
            risk_level = 'HIGH'
        
        # Set risk level based on probability if not already HIGH
        if risk_level != 'HIGH':
            if fraud_probability >= 0.4:
                risk_level = 'MEDIUM'
            elif fraud_probability >= 0.2:
                risk_level = 'LOW'
        
        # Ensure minimum fraud probability for fraud transactions
        if is_fraud and fraud_probability < 0.5:
            fraud_probability = 0.5
        
    except Exception as e:
        logger.error(f"Error in fraud detection: {e}")
    
    return {
        'is_fraud': is_fraud,
        'risk_level': risk_level,
        'fraud_probability': min(fraud_probability, 1.0),
        'fraud_reason': '; '.join(fraud_indicators) if fraud_indicators else None
    }


def calculate_risk_score(amount, transaction_type, location):
    """Calculate AI Risk Score (0-100)"""
    risk_score = 0.0
    
    # Amount-based risk
    if amount > 50000:
        risk_score += 40
    elif amount > 25000:
        risk_score += 25
    elif amount > 10000:
        risk_score += 10
    
    # Transaction type risk
    high_risk_types = ['INTERNATIONAL', 'WIRE_TRANSFER', 'CRYPTO']
    if transaction_type.upper() in high_risk_types:
        risk_score += 25
    
    # Location risk
    if location:
        if 'unknown' in location.lower():
            risk_score += 30
        elif 'test' in location.lower():
            risk_score += 50
    
    return min(int(risk_score), 100)


# ==================== ACTIVITY LOGGING ====================

def log_activity(user_id, activity_type, description, ip_address=None):
    """Log user activity"""
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO activity_logs (user_id, activity_type, description, ip_address)
            VALUES (?, ?, ?, ?)
        """, (user_id, activity_type, description, ip_address))
        db.commit()
    except Exception as e:
        logger.error(f"Error logging activity: {e}")


# ==================== SMS SIMULATION ====================

def simulate_send_sms(mobile_number, message):
    """Simulate sending SMS"""
    logger.info(f"📱 [SMS] To: {mobile_number} | Message: {message}")
    return True


# ==================== FLASK APP ====================

def create_app():
    """Create and configure Flask app"""
    app = Flask(__name__)
    app.secret_key = 'fraud-detection-secret-key-2024'
    CORS(app, supports_credentials=True)
    app.teardown_appcontext(close_connection)
    
    # Initialize database
    with app.app_context():
        init_database()
    
    # Store app config
    app.config['stream_running'] = False
    app.config['stream_thread'] = None
    
    register_routes(app)
    return app


def register_routes(app):
    """Register all API routes"""
    
    # Root endpoint
    @app.route('/')
    def index():
        return jsonify({
            'status': 'running',
            'service': 'Real-Time Fraud Detection System',
            'version': '2.0.0',
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/api/')
    def api_root():
        return jsonify({
            'status': 'running',
            'service': 'Fraud Detection API',
            'version': '2.0.0',
            'timestamp': datetime.now().isoformat(),
            'endpoints': {
                'health': '/api/health',
                'auth': '/api/register, /api/login, /api/logout, /api/current-user',
                'verification': '/api/send-otp, /api/verify-otp',
                'transactions': '/api/transactions, /api/add-transaction, /api/analyze',
                'alerts': '/api/alerts',
                'stats': '/api/stats',
                'analytics': '/api/analytics',
                'stream': '/api/start-stream, /api/stop-stream, /api/stream-status',
                'demo': '/api/generate-demo',
                'reports': '/api/download-report'
            }
        })
    
    # Health check
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'Fraud Detection API',
            'database': 'connected',
            'stream_running': app.config['stream_running'],
            'timestamp': datetime.now().isoformat()
        })
    
    # ==================== AUTHENTICATION ====================
    
    @app.route('/api/register', methods=['POST'])
    def register():
        """Register a new user"""
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        email = data.get('email', '').strip()
        mobile_number = data.get('mobile_number', '').strip()
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password required'}), 400
        
        try:
            db = get_db()
            cursor = db.cursor()
            
            # Check if user exists
            cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
            if cursor.fetchone():
                return jsonify({'success': False, 'error': 'Username or email already exists'}), 400
            
            user_id = f"USER{uuid.uuid4().hex[:8].upper()}"
            cursor.execute("""
                INSERT INTO users (user_id, username, password_hash, email, mobile_number)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, username, hash_password(password), email, mobile_number))
            db.commit()
            
            log_activity(user_id, 'REGISTER', f'User {username} registered')
            
            return jsonify({
                'success': True,
                'message': 'Registered successfully',
                'user': {'id': user_id, 'username': username}
            }), 201
            
        except Exception as e:
            logger.error(f"Registration error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/login', methods=['POST'])
    def login():
        """Login user"""
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password required'}), 400
        
        try:
            db = get_db()
            cursor = db.cursor()
            
            cursor.execute("""
                SELECT * FROM users WHERE username = ? AND password_hash = ?
            """, (username, hash_password(password)))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
            
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            
            # Check if verified
            cursor.execute('SELECT * FROM verified_users WHERE user_id = ?', (user['user_id'],))
            verified_user = cursor.fetchone()
            
            is_verified = verified_user is not None
            mobile_number = verified_user['mobile_number'] if verified_user else None
            
            log_activity(user['user_id'], 'LOGIN', f'User {username} logged in')
            
            return jsonify({
                'success': True,
                'user': {
                    'id': user['user_id'],
                    'username': user['username'],
                    'email': user['email']
                },
                'is_verified': is_verified,
                'mobile_number': mobile_number
            })
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/logout', methods=['POST'])
    def logout():
        """Logout user"""
        user_id = session.get('user_id')
        if user_id:
            log_activity(user_id, 'LOGOUT', 'User logged out')
        session.clear()
        return jsonify({'success': True})
    
    @app.route('/api/current-user', methods=['GET'])
    def current_user():
        """Get current user info"""
        if 'user_id' not in session:
            return jsonify({'success': True, 'logged_in': False, 'is_verified': False})
        
        user_id = session.get('user_id')
        username = session.get('username')
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('SELECT email FROM users WHERE user_id = ?', (user_id,))
        user_row = cursor.fetchone()
        email = user_row['email'] if user_row else None
        
        cursor.execute('SELECT * FROM verified_users WHERE user_id = ?', (user_id,))
        verified_user = cursor.fetchone()
        
        is_verified = verified_user is not None
        mobile_number = verified_user['mobile_number'] if verified_user else None
        
        return jsonify({
            'success': True,
            'logged_in': True,
            'username': username,
            'user_id': user_id,
            'email': email,
            'is_verified': is_verified,
            'mobile_number': mobile_number
        })
    
    # ==================== OTP VERIFICATION ====================
    
    @app.route('/api/send-otp', methods=['POST'])
    def send_otp():
        """Generate and send OTP"""
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        mobile_number = data.get('mobile_number', '').strip()
        user_id = session.get('user_id') or data.get('user_id', f"USER{uuid.uuid4().hex[:8].upper()}")
        
        if not mobile_number:
            return jsonify({'success': False, 'error': 'Mobile number required'}), 400
        
        # Clean mobile number
        mobile_number = ''.join(filter(str.isdigit, mobile_number))
        if len(mobile_number) < 10:
            return jsonify({'success': False, 'error': 'Invalid mobile number'}), 400
        
        if not mobile_number.startswith('+'):
            mobile_number = '+1' + mobile_number[-10:]
        
        # Generate OTP
        otp_code = generate_otp()
        expires_at = datetime.now() + timedelta(seconds=60)
        
        try:
            db = get_db()
            cursor = db.cursor()
            
            # Delete old OTPs for this number
            cursor.execute('DELETE FROM otp_store WHERE mobile_number = ? AND verified = 0', (mobile_number,))
            
            # Insert new OTP
            cursor.execute("""
                INSERT INTO otp_store (mobile_number, otp_code, user_id, expires_at)
                VALUES (?, ?, ?, ?)
            """, (mobile_number, otp_code, user_id, expires_at.isoformat()))
            db.commit()
            
            # Simulate SMS
            message = f"Your verification code is: {otp_code}. This code expires in 60 seconds."
            simulate_send_sms(mobile_number, message)
            
            logger.info(f"OTP sent to {mobile_number}: {otp_code}")
            
            return jsonify({
                'success': True,
                'message': 'OTP sent successfully',
                'expires_in': 60
            })
            
        except Exception as e:
            logger.error(f"Error sending OTP: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/verify-otp', methods=['POST'])
    def verify_otp():
        """Verify OTP and move user to verified_users"""
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        mobile_number = data.get('mobile_number', '').strip()
        otp_code = data.get('otp_code', '').strip()
        user_id = session.get('user_id') or data.get('user_id')
        
        if not mobile_number or not otp_code:
            return jsonify({'success': False, 'error': 'Mobile number and OTP required'}), 400
        
        # Clean mobile number
        mobile_number = ''.join(filter(str.isdigit, mobile_number))
        if not mobile_number.startswith('+'):
            mobile_number = '+1' + mobile_number[-10:]
        
        try:
            db = get_db()
            cursor = db.cursor()
            
            # Find OTP record
            cursor.execute("""
                SELECT * FROM otp_store 
                WHERE mobile_number = ? AND otp_code = ? AND verified = 0
                ORDER BY created_at DESC LIMIT 1
            """, (mobile_number, otp_code))
            otp_record = cursor.fetchone()
            
            if not otp_record:
                return jsonify({'success': False, 'error': 'Invalid OTP'}), 400
            
            # Check if expired
            expires_at = datetime.fromisoformat(otp_record['expires_at'])
            if datetime.now() > expires_at:
                return jsonify({'success': False, 'error': 'OTP expired'}), 400
            
            # Mark OTP as verified
            cursor.execute('UPDATE otp_store SET verified = 1 WHERE id = ?', (otp_record['id'],))
            
            # Get or create username
            username = session.get('username') or f'User_{mobile_number[-4:]}'
            
            # Get user email if exists
            cursor.execute('SELECT email FROM users WHERE user_id = ?', (user_id,))
            user_row = cursor.fetchone()
            email = user_row['email'] if user_row else None
            
            # Add to verified_users
            cursor.execute("""
                INSERT OR REPLACE INTO verified_users (user_id, username, email, mobile_number, verified_at)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id or otp_record['user_id'], username, email, mobile_number, datetime.now().isoformat()))
            
            # Update users table if exists
            if user_id:
                cursor.execute('UPDATE users SET is_verified = 1, mobile_number = ? WHERE user_id = ?', 
                              (mobile_number, user_id))
            
            db.commit()
            
            simulate_send_sms(mobile_number, f"Your mobile number {mobile_number} has been verified.")
            log_activity(user_id, 'OTP_VERIFIED', f'Mobile {mobile_number} verified')
            
            return jsonify({
                'success': True,
                'message': 'Mobile number verified successfully',
                'mobile_number': mobile_number
            })
            
        except Exception as e:
            logger.error(f"Error verifying OTP: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ==================== TRANSACTIONS ====================
    
    @app.route('/api/transactions', methods=['GET'])
    def get_transactions():
        """Get transactions with optional filters"""
        user_id = request.args.get('user_id')
        limit = min(int(request.args.get('limit', 50)), 100)
        risk_level = request.args.get('risk_level')
        is_fraud = request.args.get('is_fraud')
        
        try:
            db = get_db()
            cursor = db.cursor()
            
            query = "SELECT * FROM transactions"
            params = []
            conditions = []
            
            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)
            
            if risk_level:
                conditions.append("risk_level = ?")
                params.append(risk_level)
            
            if is_fraud is not None:
                conditions.append("is_fraud = ?")
                params.append(1 if is_fraud.lower() == 'true' else 0)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            transactions = []
            for row in rows:
                transactions.append({
                    'id': row['id'],
                    'transaction_id': row['transaction_id'],
                    'user_id': row['user_id'],
                    'amount': row['amount'],
                    'transaction_type': row['transaction_type'],
                    'receiver_account': row['receiver_account'],
                    'location': row['location'],
                    'timestamp': row['timestamp'],
                    'is_fraud': bool(row['is_fraud']),
                    'fraud_reason': row['fraud_reason'],
                    'risk_level': row['risk_level'],
                    'fraud_probability': row['fraud_probability'],
                    'merchant': row['merchant'],
                    'description': row['description']
                })
            
            return jsonify({
                'success': True,
                'count': len(transactions),
                'transactions': transactions
            })
            
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/add-transaction', methods=['POST'])
    def add_transaction():
        """Add a new transaction with fraud detection"""
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        try:
            user_id = data.get('user_id', 'GUEST')
            amount = float(data.get('amount', 0))
            
            if amount <= 0:
                return jsonify({'success': False, 'error': 'Invalid amount'}), 400
            
            transaction = {
                'transaction_id': data.get('transaction_id') or generate_transaction_id(),
                'user_id': user_id,
                'amount': amount,
                'transaction_type': data.get('transaction_type', 'TRANSFER'),
                'receiver_account': data.get('receiver_account', ''),
                'location': data.get('location', 'Online'),
                'timestamp': datetime.now().isoformat(),
                'merchant': data.get('merchant', ''),
                'description': data.get('description', '')
            }
            
            # Run fraud detection
            fraud_result = detect_fraud(transaction)
            transaction['is_fraud'] = fraud_result['is_fraud']
            transaction['risk_level'] = fraud_result['risk_level']
            transaction['fraud_probability'] = fraud_result['fraud_probability']
            transaction['fraud_reason'] = fraud_result['fraud_reason']
            
            # Save to database
            db = get_db()
            cursor = db.cursor()
            
            cursor.execute("""
                INSERT INTO transactions (
                    transaction_id, user_id, amount, transaction_type, receiver_account,
                    location, timestamp, is_fraud, fraud_reason, risk_level, fraud_probability,
                    merchant, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                transaction['transaction_id'],
                transaction['user_id'],
                transaction['amount'],
                transaction['transaction_type'],
                transaction['receiver_account'],
                transaction['location'],
                transaction['timestamp'],
                1 if transaction['is_fraud'] else 0,
                transaction['fraud_reason'],
                transaction['risk_level'],
                transaction['fraud_probability'],
                transaction['merchant'],
                transaction['description']
            ))
            
            # Create alert if fraud detected
            if transaction['is_fraud']:
                alert_id = f"ALT{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100, 999)}"
                cursor.execute("""
                    INSERT INTO alerts (
                        alert_id, transaction_id, user_id, amount, alert_type,
                        alert_message, risk_level, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert_id,
                    transaction['transaction_id'],
                    transaction['user_id'],
                    transaction['amount'],
                    'FRAUD_DETECTED',
                    transaction['fraud_reason'],
                    transaction['risk_level'],
                    'new'
                ))
                
                # Try to send SMS to verified user
                cursor.execute('SELECT mobile_number FROM verified_users WHERE user_id = ?', (user_id,))
                verified = cursor.fetchone()
                if verified:
                    message = f"🚨 FRAUD ALERT: Suspicious transaction of ₹{amount:,.2f} detected. Reason: {transaction['fraud_reason']}"
                    simulate_send_sms(verified['mobile_number'], message)
                
                logger.warning(f"🚨 FRAUD DETECTED: {transaction['transaction_id']} - ₹{amount:,.2f}")
            
            db.commit()
            log_activity(user_id, 'TRANSACTION', f'New transaction: {transaction["transaction_id"]}')
            
            return jsonify({
                'success': True,
                'transaction': transaction,
                'fraud_detection': fraud_result
            }), 201
            
        except Exception as e:
            logger.error(f"Error adding transaction: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/analyze', methods=['POST'])
    def analyze_transaction():
        """Analyze a transaction for fraud"""
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        try:
            user_id = session.get('user_id') or data.get('user_id', 'GUEST')
            
            transaction = {
                'user_id': user_id,
                'amount': float(data.get('amount', 0)),
                'transaction_type': data.get('transaction_type', 'TRANSFER'),
                'receiver_account': data.get('receiver_account', ''),
                'location': data.get('location', 'Online'),
                'timestamp': datetime.now().isoformat()
            }
            
            if transaction['amount'] <= 0:
                return jsonify({'success': False, 'error': 'Invalid amount'}), 400
            
            # Calculate AI risk score
            risk_score = calculate_risk_score(
                transaction['amount'],
                transaction['transaction_type'],
                transaction['location']
            )
            
            # Run fraud detection
            fraud_result = detect_fraud(transaction)
            
            return jsonify({
                'success': True,
                'transaction': transaction,
                'analysis': {
                    'risk_score': risk_score,
                    'risk_level': 'HIGH' if risk_score >= 71 else 'MEDIUM' if risk_score >= 31 else 'LOW',
                    'is_fraud': fraud_result['is_fraud'],
                    'fraud_probability': fraud_result['fraud_probability'],
                    'fraud_reason': fraud_result['fraud_reason']
                }
            })
            
        except Exception as e:
            logger.error(f"Error analyzing transaction: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ==================== ALERTS ====================
    
    @app.route('/api/alerts', methods=['GET'])
    def get_alerts():
        """Get fraud alerts"""
        user_id = request.args.get('user_id')
        status = request.args.get('status')
        limit = min(int(request.args.get('limit', 50)), 100)
        
        try:
            db = get_db()
            cursor = db.cursor()
            
            query = "SELECT * FROM alerts"
            params = []
            conditions = []
            
            if user_id:
                conditions.append("user_id = ?")
                params.append(user_id)
            
            if status:
                conditions.append("status = ?")
                params.append(status)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY alert_time DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            alerts = []
            for row in rows:
                alerts.append({
                    'id': row['id'],
                    'alert_id': row['alert_id'],
                    'transaction_id': row['transaction_id'],
                    'user_id': row['user_id'],
                    'amount': row['amount'],
                    'alert_type': row['alert_type'],
                    'alert_message': row['alert_message'],
                    'risk_level': row['risk_level'],
                    'status': row['status'],
                    'alert_time': row['alert_time']
                })
            
            return jsonify({
                'success': True,
                'count': len(alerts),
                'alerts': alerts
            })
            
        except Exception as e:
            logger.error(f"Error getting alerts: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/alerts/<alert_id>', methods=['PUT'])
    def update_alert(alert_id):
        """Update alert status"""
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'success': False, 'error': 'Status required'}), 400
        
        try:
            db = get_db()
            cursor = db.cursor()
            
            if alert_id.isdigit():
                cursor.execute('UPDATE alerts SET status = ? WHERE id = ?', (new_status, int(alert_id)))
            else:
                cursor.execute('UPDATE alerts SET status = ? WHERE alert_id = ?', (new_status, alert_id))
            
            db.commit()
            
            return jsonify({'success': True, 'status': new_status})
            
        except Exception as e:
            logger.error(f"Error updating alert: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ==================== STATISTICS ====================
    
    @app.route('/api/stats', methods=['GET'])
    def get_stats():
        """Get transaction statistics"""
        user_id = request.args.get('user_id')
        
        try:
            db = get_db()
            cursor = db.cursor()
            
            if user_id:
                # User-specific stats
                cursor.execute('SELECT COUNT(*) as count FROM transactions WHERE user_id = ?', (user_id,))
                total_txn = cursor.fetchone()['count'] or 0
                
                cursor.execute('SELECT COUNT(*) as count FROM transactions WHERE user_id = ? AND is_fraud = 1', (user_id,))
                fraud_txn = cursor.fetchone()['count'] or 0
                
                cursor.execute('SELECT SUM(amount) as total FROM transactions WHERE user_id = ?', (user_id,))
                total_amount = cursor.fetchone()['total'] or 0
                
                cursor.execute('SELECT COUNT(*) as count FROM alerts WHERE user_id = ? AND status = ?', (user_id, 'new'))
                new_alerts = cursor.fetchone()['count'] or 0
                
                cursor.execute('SELECT COUNT(*) as count FROM alerts WHERE user_id = ?', (user_id,))
                total_alerts = cursor.fetchone()['count'] or 0
            else:
                # Global stats
                cursor.execute('SELECT COUNT(*) as count FROM transactions')
                total_txn = cursor.fetchone()['count'] or 0
                
                cursor.execute('SELECT COUNT(*) as count FROM transactions WHERE is_fraud = 1')
                fraud_txn = cursor.fetchone()['count'] or 0
                
                cursor.execute('SELECT SUM(amount) as total FROM transactions')
                total_amount = cursor.fetchone()['total'] or 0
                
                cursor.execute('SELECT COUNT(*) as count FROM alerts WHERE status = ?', ('new',))
                new_alerts = cursor.fetchone()['count'] or 0
                
                cursor.execute('SELECT COUNT(*) as count FROM alerts')
                total_alerts = cursor.fetchone()['count'] or 0
            
            # Risk distribution
            cursor.execute('SELECT risk_level, COUNT(*) as count FROM transactions GROUP BY risk_level')
            risk_distribution = {}
            for row in cursor.fetchall():
                risk_distribution[row['risk_level']] = row['count']
            
            # High risk count
            cursor.execute('SELECT COUNT(*) as count FROM transactions WHERE risk_level = ?', ('HIGH',))
            high_risk = cursor.fetchone()['count'] or 0
            
            return jsonify({
                'success': True,
                'stats': {
                    'total_transactions': total_txn,
                    'fraud_transactions': fraud_txn,
                    'normal_transactions': total_txn - fraud_txn,
                    'fraud_percentage': round(fraud_txn / total_txn * 100, 2) if total_txn > 0 else 0,
                    'total_amount': round(total_amount, 2),
                    'total_alerts': total_alerts,
                    'new_alerts': new_alerts,
                    'high_risk_transactions': high_risk,
                    'risk_distribution': risk_distribution,
                    'timestamp': datetime.now().isoformat()
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ==================== ANALYTICS ====================
    
    @app.route('/api/analytics', methods=['GET'])
    def get_analytics():
        """Get analytics data"""
        user_id = request.args.get('user_id')
        
        try:
            db = get_db()
            cursor = db.cursor()
            
            # Transactions by type
            if user_id:
                cursor.execute("""
                    SELECT transaction_type, COUNT(*) as count, SUM(amount) as total
                    FROM transactions WHERE user_id = ?
                    GROUP BY transaction_type
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT transaction_type, COUNT(*) as count, SUM(amount) as total
                    FROM transactions GROUP BY transaction_type
                """)
            
            type_data = []
            for row in cursor.fetchall():
                type_data.append({
                    'type': row['transaction_type'] or 'UNKNOWN',
                    'count': row['count'],
                    'total': row['total'] or 0
                })
            
            # Daily trend (last 7 days)
            if user_id:
                cursor.execute("""
                    SELECT DATE(timestamp) as date, 
                           COUNT(*) as total_transactions,
                           SUM(is_fraud) as fraud_transactions,
                           SUM(amount) as total_amount
                    FROM transactions 
                    WHERE user_id = ? AND timestamp > datetime('now', '-7 days')
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT DATE(timestamp) as date, 
                           COUNT(*) as total_transactions,
                           SUM(is_fraud) as fraud_transactions,
                           SUM(amount) as total_amount
                    FROM transactions 
                    WHERE timestamp > datetime('now', '-7 days')
                    GROUP BY DATE(timestamp)
                    ORDER BY date
                """)
            
            daily_data = []
            for row in cursor.fetchall():
                daily_data.append({
                    'date': row['date'],
                    'total_transactions': row['total_transactions'],
                    'fraud_transactions': row['fraud_transactions'] or 0,
                    'total_amount': row['total_amount'] or 0
                })
            
            # Top suspicious transactions
            if user_id:
                cursor.execute("""
                    SELECT * FROM transactions 
                    WHERE is_fraud = 1 AND user_id = ?
                    ORDER BY fraud_probability DESC, timestamp DESC
                    LIMIT 10
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT * FROM transactions 
                    WHERE is_fraud = 1
                    ORDER BY fraud_probability DESC, timestamp DESC
                    LIMIT 10
                """)
            
            suspicious = []
            for row in cursor.fetchall():
                suspicious.append({
                    'transaction_id': row['transaction_id'],
                    'amount': row['amount'],
                    'risk_level': row['risk_level'],
                    'fraud_reason': row['fraud_reason'],
                    'timestamp': row['timestamp']
                })
            
            # Recent activity
            if user_id:
                cursor.execute("""
                    SELECT * FROM activity_logs 
                    WHERE user_id = ?
                    ORDER BY timestamp DESC LIMIT 20
                """, (user_id,))
            else:
                cursor.execute("""
                    SELECT * FROM activity_logs 
                    ORDER BY timestamp DESC LIMIT 20
                """)
            
            activities = []
            for row in cursor.fetchall():
                activities.append({
                    'type': row['activity_type'],
                    'description': row['description'],
                    'timestamp': row['timestamp']
                })
            
            # Top suspicious accounts
            cursor.execute("""
                SELECT user_id, 
                       COUNT(*) as total_transactions,
                       SUM(is_fraud) as fraud_count,
                       AVG(fraud_probability) as avg_risk
                FROM transactions 
                GROUP BY user_id
                HAVING fraud_count > 0
                ORDER BY fraud_count DESC, avg_risk DESC
                LIMIT 10
            """)
            
            suspicious_accounts = []
            for row in cursor.fetchall():
                suspicious_accounts.append({
                    'user_id': row['user_id'],
                    'total_transactions': row['total_transactions'],
                    'fraud_count': row['fraud_count'] or 0,
                    'average_risk_score': round((row['avg_risk'] or 0) * 100, 1)
                })
            
            return jsonify({
                'success': True,
                'analytics': {
                    'by_type': type_data,
                    'daily': daily_data,
                    'suspicious': suspicious,
                    'recent_activity': activities,
                    'suspicious_accounts': suspicious_accounts
                }
            })
            
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ==================== REAL-TIME STREAM ====================
    
    @app.route('/api/start-stream', methods=['POST'])
    def start_stream():
        """Start generating demo transactions"""
        global stream_running, stream_thread
        
        if app.config['stream_running']:
            return jsonify({
                'success': True,
                'message': 'Stream already running',
                'running': True
            })
        
        app.config['stream_running'] = True
        
        def generate_transactions():
            """Background thread for generating transactions"""
            while app.config['stream_running']:
                try:
                    # Generate random transaction
                    user_id = random.choice(USER_IDS)
                    
                    # 15% chance of fraud transaction
                    is_fraud_transaction = random.random() < 0.15
                    
                    if is_fraud_transaction:
                        # Generate high amount fraud
                        amount = random.choice([
                            random.uniform(50001, 75000),
                            random.uniform(75001, 150000)
                        ])
                        location = random.choice(["Unknown Location", "Test Location", "Dark Web"])
                    else:
                        # Normal transaction
                        amount = random.uniform(100, 49000)
                        location = random.choice(DEMO_LOCATIONS)
                    
                    transaction = {
                        'transaction_id': generate_transaction_id(),
                        'user_id': user_id,
                        'amount': round(amount, 2),
                        'transaction_type': random.choice(['TRANSFER', 'UPI', 'CARD', 'CASH_WITHDRAWAL']),
                        'receiver_account': f"ACC{random.randint(100000, 999999)}",
                        'location': location,
                        'timestamp': datetime.now().isoformat(),
                        'merchant': random.choice(DEMO_MERCHANTS),
                        'description': f"Payment to {random.choice(DEMO_MERCHANTS)}"
                    }
                    
                    # Run fraud detection
                    fraud_result = detect_fraud(transaction)
                    transaction['is_fraud'] = fraud_result['is_fraud']
                    transaction['risk_level'] = fraud_result['risk_level']
                    transaction['fraud_probability'] = fraud_result['fraud_probability']
                    transaction['fraud_reason'] = fraud_result['fraud_reason']
                    
                    # Save to database
                    db = get_db()
                    cursor = db.cursor()
                    
                    cursor.execute("""
                        INSERT INTO transactions (
                            transaction_id, user_id, amount, transaction_type, receiver_account,
                            location, timestamp, is_fraud, fraud_reason, risk_level, fraud_probability,
                            merchant, description
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        transaction['transaction_id'],
                        transaction['user_id'],
                        transaction['amount'],
                        transaction['transaction_type'],
                        transaction['receiver_account'],
                        transaction['location'],
                        transaction['timestamp'],
                        1 if transaction['is_fraud'] else 0,
                        transaction['fraud_reason'],
                        transaction['risk_level'],
                        transaction['fraud_probability'],
                        transaction['merchant'],
                        transaction['description']
                    ))
                    
                    # Create alert if fraud detected
                    if transaction['is_fraud']:
                        alert_id = f"ALT{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100, 999)}"
                        cursor.execute("""
                            INSERT INTO alerts (
                                alert_id, transaction_id, user_id, amount, alert_type,
                                alert_message, risk_level, status
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            alert_id,
                            transaction['transaction_id'],
                            transaction['user_id'],
                            transaction['amount'],
                            'FRAUD_DETECTED',
                            transaction['fraud_reason'],
                            transaction['risk_level'],
                            'new'
                        ))
                        
                        logger.warning(f"🚨 FRAUD DETECTED: {transaction['transaction_id']} - ₹{transaction['amount']:,.2f}")
                    
                    db.commit()
                    
                    # Sleep for 2-4 seconds between transactions
                    time.sleep(random.uniform(2, 4))
                    
                except Exception as e:
                    logger.error(f"Error generating transaction: {e}")
                    time.sleep(1)
        
        stream_thread = threading.Thread(target=generate_transactions)
        stream_thread.daemon = True
        stream_thread.start()
        
        logger.info("Transaction stream started")
        
        return jsonify({
            'success': True,
            'message': 'Transaction stream started',
            'running': True
        })
    
    @app.route('/api/stop-stream', methods=['POST'])
    def stop_stream():
        """Stop generating transactions"""
        app.config['stream_running'] = False
        logger.info("Transaction stream stopped")
        
        return jsonify({
            'success': True,
            'message': 'Transaction stream stopped',
            'running': False
        })
    
    @app.route('/api/stream-status', methods=['GET'])
    def stream_status():
        """Get stream status"""
        return jsonify({
            'success': True,
            'running': app.config['stream_running']
        })
    
    # ==================== DEMO GENERATOR ====================
    
    @app.route('/api/generate-demo', methods=['POST'])
    def generate_demo():
        """Generate demo transactions (single call)"""
        data = request.get_json() or {}
        count = min(int(data.get('count', 10)), 50)
        
        try:
            db = get_db()
            cursor = db.cursor()
            
            generated = 0
            fraud_count = 0
            
            for _ in range(count):
                # 20% chance of fraud
                is_fraud_transaction = random.random() < 0.20
                
                if is_fraud_transaction:
                    amount = random.uniform(50001, 150000)
                    location = random.choice(["Unknown Location", "Test Location", "Offshore"])
                else:
                    amount = random.uniform(100, 49000)
                    location = random.choice(DEMO_LOCATIONS)
                
                transaction = {
                    'transaction_id': generate_transaction_id(),
                    'user_id': random.choice(USER_IDS),
                    'amount': round(amount, 2),
                    'transaction_type': random.choice(['TRANSFER', 'UPI', 'CARD', 'CASH_WITHDRAWAL']),
                    'receiver_account': f"ACC{random.randint(100000, 999999)}",
                    'location': location,
                    'timestamp': datetime.now().isoformat(),
                    'merchant': random.choice(DEMO_MERCHANTS),
                    'description': f"Demo payment"
                }
                
                fraud_result = detect_fraud(transaction)
                transaction['is_fraud'] = fraud_result['is_fraud']
                transaction['risk_level'] = fraud_result['risk_level']
                transaction['fraud_probability'] = fraud_result['fraud_probability']
                transaction['fraud_reason'] = fraud_result['fraud_reason']
                
                cursor.execute("""
                    INSERT INTO transactions (
                        transaction_id, user_id, amount, transaction_type, receiver_account,
                        location, timestamp, is_fraud, fraud_reason, risk_level, fraud_probability,
                        merchant, description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    transaction['transaction_id'],
                    transaction['user_id'],
                    transaction['amount'],
                    transaction['transaction_type'],
                    transaction['receiver_account'],
                    transaction['location'],
                    transaction['timestamp'],
                    1 if transaction['is_fraud'] else 0,
                    transaction['fraud_reason'],
                    transaction['risk_level'],
                    transaction['fraud_probability'],
                    transaction['merchant'],
                    transaction['description']
                ))
                
                if transaction['is_fraud']:
                    fraud_count += 1
                    alert_id = f"ALT{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100, 999)}"
                    cursor.execute("""
                        INSERT INTO alerts (alert_id, transaction_id, user_id, amount, alert_type, alert_message, risk_level, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (alert_id, transaction['transaction_id'], transaction['user_id'], transaction['amount'],
                          'FRAUD_DETECTED', transaction['fraud_reason'], transaction['risk_level'], 'new'))
                
                generated += 1
            
            db.commit()
            
            return jsonify({
                'success': True,
                'message': f'Generated {generated} demo transactions',
                'generated': generated,
                'fraud_detected': fraud_count
            })
            
        except Exception as e:
            logger.error(f"Error generating demo: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ==================== REPORTS ====================
    
    @app.route('/api/download-report', methods=['GET'])
    def download_report():
        """Download transaction report as CSV"""
        try:
            db = get_db()
            cursor = db.cursor()
            
            cursor.execute("""
                SELECT transaction_id, user_id, amount, transaction_type, 
                       location, timestamp, is_fraud, risk_level, fraud_probability
                FROM transactions
                ORDER BY timestamp DESC
                LIMIT 1000
            """)
            
            # Create CSV
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Transaction ID', 'User ID', 'Amount', 'Type', 'Location', 
                           'Timestamp', 'Is Fraud', 'Risk Level', 'Fraud Probability'])
            
            for row in cursor.fetchall():
                writer.writerow([
                    row['transaction_id'],
                    row['user_id'],
                    row['amount'],
                    row['transaction_type'],
                    row['location'],
                    row['timestamp'],
                    'Yes' if row['is_fraud'] else 'No',
                    row['risk_level'],
                    f"{row['fraud_probability']:.2%}"
                ])
            
            output.seek(0)
            
            return send_file(
                io.BytesIO(output.getvalue().encode('utf-8')),
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'fraud_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
            )
            
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # ==================== BANK STATEMENT UPLOAD ====================
    
    @app.route('/api/upload-statement', methods=['POST'])
    def upload_statement():
        """Upload and analyze bank statement CSV"""
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'error': 'Only CSV files allowed'}), 400
        
        try:
            content = file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
            
            user_id = session.get('user_id') or 'GUEST'
            
            transactions_analyzed = 0
            suspicious_count = 0
            total_amount = 0.0
            analyzed_transactions = []
            
            db = get_db()
            cursor = db.cursor()
            
            for row in csv_reader:
                # Extract transaction data
                amount = float(row.get('amount', row.get('Amount', row.get('Debit', 0))))
                if amount <= 0:
                    continue
                
                transaction = {
                    'transaction_id': generate_transaction_id(),
                    'user_id': user_id,
                    'amount': amount,
                    'transaction_type': row.get('type', row.get('Type', 'TRANSFER')),
                    'receiver_account': row.get('receiver', row.get('Receiver', '')),
                    'location': row.get('location', row.get('Location', 'Online')),
                    'timestamp': row.get('date', row.get('Date', datetime.now().isoformat())),
                    'description': row.get('description', row.get('Description', ''))
                }
                
                total_amount += amount
                
                # Run fraud detection
                fraud_result = detect_fraud(transaction)
                transaction['is_fraud'] = fraud_result['is_fraud']
                transaction['risk_level'] = fraud_result['risk_level']
                transaction['fraud_probability'] = fraud_result['fraud_probability']
                transaction['fraud_reason'] = fraud_result['fraud_reason']
                
                if fraud_result['is_fraud']:
                    suspicious_count += 1
                
                # Save transaction
                cursor.execute("""
                    INSERT INTO transactions (
                        transaction_id, user_id, amount, transaction_type, receiver_account,
                        location, timestamp, is_fraud, fraud_reason, risk_level, fraud_probability, description
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    transaction['transaction_id'], transaction['user_id'], transaction['amount'],
                    transaction['transaction_type'], transaction['receiver_account'], transaction['location'],
                    transaction['timestamp'], 1 if transaction['is_fraud'] else 0,
                    transaction['fraud_reason'], transaction['risk_level'],
                    transaction['fraud_probability'], transaction['description']
                ))
                
                transactions_analyzed += 1
                analyzed_transactions.append(transaction)
            
            # Save bank statement record
            statement_id = f"STM{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(100, 999)}"
            cursor.execute("""
                INSERT INTO bank_statements (statement_id, user_id, filename, total_transactions, total_amount, suspicious_count, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (statement_id, user_id, file.filename, transactions_analyzed, total_amount, suspicious_count, 'completed'))
            
            db.commit()
            log_activity(user_id, 'UPLOAD', f'Uploaded bank statement: {file.filename}')
            
            return jsonify({
                'success': True,
                'message': f'Successfully analyzed {transactions_analyzed} transactions',
                'results': {
                    'total_transactions': transactions_analyzed,
                    'total_amount': total_amount,
                    'suspicious_transactions': suspicious_count,
                    'transactions': analyzed_transactions[-20:]
                }
            })
            
        except Exception as e:
            logger.error(f"Error processing bank statement: {e}")
