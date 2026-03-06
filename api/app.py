"""
Flask Backend API - Real-Time Fraud Detection System
With OTP Verification, SMS Alert, Email Alert and Call Fraud Detection Features
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
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, session, g
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from models.fraud_detector import FraudDetector
from streaming.transaction_generator import TransactionGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


running = False
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fraud_detection.db')


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    cursor = db.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS verified_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT UNIQUE NOT NULL,
        username TEXT,
        mobile_number TEXT UNIQUE NOT NULL,
        verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS otp_store (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mobile_number TEXT NOT NULL,
        otp_code TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        verified BOOLEAN DEFAULT 0,
        user_id TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        transaction_id TEXT NOT NULL,
        mobile_number TEXT NOT NULL,
        amount REAL NOT NULL,
        alert_message TEXT,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'sent')''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS call_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        caller_number TEXT NOT NULL,
        recipient_number TEXT NOT NULL,
        call_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'pending',
        user_id TEXT,
        otp_verified BOOLEAN DEFAULT 0)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS suspicious_activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        user_number TEXT NOT NULL,
        activity_type TEXT NOT NULL,
        description TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        alert_status TEXT DEFAULT 'pending',
        sms_sent BOOLEAN DEFAULT 0,
        email_sent BOOLEAN DEFAULT 0)''')
    
    db.commit()
    db.close()
    logger.info("Database initialized successfully")


def generate_otp():
    return ''.join([str(random.randint(0, 9)) for _ in range(config.OTP_LENGTH)])


def is_otp_expired(expires_at):
    try:
        expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        return datetime.now() > expires_datetime
    except:
        return True


def simulate_send_sms(mobile_number, message):
    if config.SMS_SIMULATION_LOG:
        logger.info(f"📱 [SMS SIMULATION] To: {mobile_number}")
        logger.info(f"   Message: {message}")
        logger.info("-" * 50)
    return True


def send_email_alert(recipient_email, subject, message_body):
    if config.EMAIL_SIMULATION:
        logger.info(f"📧 [EMAIL SIMULATION] To: {recipient_email}")
        logger.info(f"   Subject: {subject}")
        logger.info(f"   Body: {message_body}")
        logger.info("-" * 50)
        return True
    
    if not config.EMAIL_ENABLED:
        logger.info("Email alerts disabled")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = config.EMAIL_FROM
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(message_body, 'plain'))
        
        server = smtplib.SMTP(config.EMAIL_HOST, config.EMAIL_PORT)
        server.starttls()
        server.login(config.EMAIL_USERNAME, config.EMAIL_PASSWORD)
        server.sendmail(config.EMAIL_FROM, recipient_email, msg.as_string())
        server.quit()
        
        logger.info(f"Email sent to {recipient_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False


def create_app():
    app = Flask(__name__)
    app.secret_key = 'fraud-detection-secret-key-2024'
    CORS(app, supports_credentials=True)
    app.teardown_appcontext(close_connection)
    
    with app.app_context():
        init_db()
    
    app.config['fraud_detector'] = FraudDetector(config.MODEL_PATH)
    app.config['transaction_generator'] = TransactionGenerator()
    app.config['transactions'] = []
    app.config['alerts'] = []
    app.config['users'] = []
    app.config['call_logs'] = []
    app.config['suspicious_activities'] = []
    app.config['call_otp_store'] = {}
    
    register_routes(app)
    return app


def register_routes(app):
    @app.route('/')
    def index():
        return jsonify({'status': 'running', 'service': 'Fraud Detection API', 'version': '4.0.0', 'timestamp': datetime.now().isoformat()})
    
    @app.route('/api/')
    def api_root():
        return jsonify({
            'status': 'running', 
            'service': 'Fraud Detection API', 
            'version': '4.0.0', 
            'timestamp': datetime.now().isoformat(),
            'endpoints': {
                'transactions': '/api/transactions',
                'recent_transactions': '/api/recent-transactions',
                'alerts': '/api/alerts',
                'stats': '/api/stats',
                'health': '/api/health',
                'send_otp': '/api/send-otp',
                'verify_otp': '/api/verify-otp',
                'verification_status': '/api/verification-status',
                'user_alerts': '/api/user-alerts',
                'attempt_call': '/api/attempt-call',
                'verify_call_otp': '/api/verify-call-otp',
                'suspicious_activities': '/api/suspicious-activities',
                'admin_stats': '/api/admin/stats',
                'admin_all_activities': '/api/admin/all-activities'
            }
        })
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy', 
            'service': 'Fraud Detection API',
            'ml_model': 'loaded' if app.config['fraud_detector'].initialized else 'rule-based',
            'transactions_count': len(app.config['transactions']),
            'alerts_count': len(app.config['alerts']),
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/api/register', methods=['POST'])
    def register():
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password required'}), 400
        
        users = app.config['users']
        if any(u['username'] == username for u in users):
            return jsonify({'success': False, 'error': 'Username exists'}), 400
        
        user = {'id': str(uuid.uuid4()), 'username': username, 'password_hash': hash_password(password), 'created_at': datetime.now().isoformat()}
        users.append(user)
        return jsonify({'success': True, 'message': 'Registered', 'user': {'id': user['id'], 'username': user['username']}}), 201
    
    @app.route('/api/login', methods=['POST'])
    def login():
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        users = app.config['users']
        user = next((u for u in users if u['username'] == username and u['password_hash'] == hash_password(password)), None)
        
        if not user:
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401
        
        session['user_id'] = user['id']
        session['username'] = user['username']
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM verified_users WHERE user_id = ?', (user['id'],))
        verified_user = cursor.fetchone()
        
        is_verified = verified_user is not None
        mobile_number = verified_user['mobile_number'] if verified_user else None
        
        return jsonify({'success': True, 'user': {'id': user['id'], 'username': user['username']}, 'is_verified': is_verified, 'mobile_number': mobile_number})
    
    @app.route('/api/logout', methods=['POST'])
    def logout():
        session.clear()
        return jsonify({'success': True})
    
    @app.route('/api/current-user', methods=['GET'])
    def current_user():
        if 'user_id' not in session:
            return jsonify({'success': False, 'logged_in': False}), 401
        
        user_id = session.get('user_id')
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM verified_users WHERE user_id = ?', (user_id,))
        verified_user = cursor.fetchone()
        
        is_verified = verified_user is not None
        mobile_number = verified_user['mobile_number'] if verified_user else None
        
        return jsonify({'success': True, 'logged_in': True, 'username': session.get('username'), 'user_id': user_id, 'is_verified': is_verified, 'mobile_number': mobile_number})
    
    @app.route('/api/send-otp', methods=['POST'])
    def send_otp():
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        mobile_number = data.get('mobile_number', '').strip()
        user_id = session.get('user_id') or data.get('user_id')
        
        if not mobile_number:
            return jsonify({'success': False, 'error': 'Mobile number required'}), 400
        
        mobile_number = ''.join(filter(str.isdigit, mobile_number))
        if len(mobile_number) < 10:
            return jsonify({'success': False, 'error': 'Invalid mobile number'}), 400
        
        if not mobile_number.startswith('+'):
            mobile_number = '+1' + mobile_number[-10:]
        
        otp_code = generate_otp()
        expires_at = datetime.now() + timedelta(seconds=config.OTP_EXPIRY_SECONDS)
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('DELETE FROM otp_store WHERE mobile_number = ? AND verified = 0', (mobile_number,))
        cursor.execute('INSERT INTO otp_store (mobile_number, otp_code, expires_at, user_id) VALUES (?, ?, ?, ?)', (mobile_number, otp_code, expires_at.isoformat(), user_id))
        db.commit()
        
        message = f"Your Fraud Detection verification code is: {otp_code}. This code expires in 5 minutes."
        simulate_send_sms(mobile_number, message)
        
        logger.info(f"OTP sent to {mobile_number}: {otp_code}")
        
        return jsonify({'success': True, 'message': 'OTP sent successfully', 'expires_in': config.OTP_EXPIRY_SECONDS})
    
    @app.route('/api/verify-otp', methods=['POST'])
    def verify_otp():
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        mobile_number = data.get('mobile_number', '').strip()
        otp_code = data.get('otp_code', '').strip()
        user_id = session.get('user_id') or data.get('user_id')
        
        if not mobile_number or not otp_code:
            return jsonify({'success': False, 'error': 'Mobile number and OTP required'}), 400
        
        mobile_number = ''.join(filter(str.isdigit, mobile_number))
        if not mobile_number.startswith('+'):
            mobile_number = '+1' + mobile_number[-10:]
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM otp_store WHERE mobile_number = ? AND otp_code = ? AND verified = 0 ORDER BY created_at DESC LIMIT 1', (mobile_number, otp_code))
        otp_record = cursor.fetchone()
        
        if not otp_record:
            return jsonify({'success': False, 'error': 'Invalid OTP'}), 400
        
        if is_otp_expired(otp_record['expires_at']):
            return jsonify({'success': False, 'error': 'OTP expired'}), 400
        
        cursor.execute('UPDATE otp_store SET verified = 1 WHERE id = ?', (otp_record['id'],))
        
        username = session.get('username') or f'User_{mobile_number[-4:]}'
        cursor.execute('INSERT OR REPLACE INTO verified_users (user_id, username, mobile_number, verified_at) VALUES (?, ?, ?, ?)', (user_id or str(uuid.uuid4()), username, mobile_number, datetime.now().isoformat()))
        db.commit()
        
        message = f"Your mobile number {mobile_number} has been verified for Fraud Detection alerts."
        simulate_send_sms(mobile_number, message)
        
        logger.info(f"User verified: {mobile_number}")
        
        return jsonify({'success': True, 'message': 'Mobile number verified successfully', 'mobile_number': mobile_number})
    
    @app.route('/api/verification-status', methods=['GET'])
    def get_verification_status():
        user_id = session.get('user_id') or request.args.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID required'}), 400
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM verified_users WHERE user_id = ?', (user_id,))
        verified_user = cursor.fetchone()
        
        if verified_user:
            return jsonify({'success': True, 'is_verified': True, 'mobile_number': verified_user['mobile_number'], 'verified_at': verified_user['verified_at']})
        else:
            return jsonify({'success': True, 'is_verified': False, 'mobile_number': None})
    
    @app.route('/api/send-fraud-alert', methods=['POST'])
    def send_fraud_alert():
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        user_id = data.get('user_id')
        transaction_id = data.get('transaction_id')
        amount = data.get('amount')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID required'}), 400
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM verified_users WHERE user_id = ?', (user_id,))
        verified_user = cursor.fetchone()
        
        if not verified_user:
            return jsonify({'success': False, 'error': 'User not verified'}), 400
        
        mobile_number = verified_user['mobile_number']
        message = f"🚨 FRAUD ALERT: Suspicious transaction of ${amount:.2f} detected on your account (ID: {transaction_id}). If this wasn't you, contact your bank immediately."
        
        simulate_send_sms(mobile_number, message)
        
        cursor.execute('INSERT INTO user_alerts (user_id, transaction_id, mobile_number, amount, alert_message) VALUES (?, ?, ?, ?, ?)', (user_id, transaction_id, mobile_number, amount, message))
        db.commit()
        
        logger.info(f"Fraud alert sent to {mobile_number} for transaction {transaction_id}")
        
        return jsonify({'success': True, 'message': 'Fraud alert sent', 'mobile_number': mobile_number})
    
    @app.route('/api/user-alerts', methods=['GET'])
    def get_user_alerts():
        user_id = session.get('user_id') or request.args.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'error': 'User ID required'}), 400
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM user_alerts WHERE user_id = ? ORDER BY sent_at DESC LIMIT 50', (user_id,))
        
        alerts = []
        for row in cursor.fetchall():
            alerts.append({'id': row['id'], 'transaction_id': row['transaction_id'], 'amount': row['amount'], 'alert_message': row['alert_message'], 'sent_at': row['sent_at'], 'status': row['status']})
        
        return jsonify({'success': True, 'count': len(alerts), 'alerts': alerts})
    
    @app.route('/api/transactions', methods=['GET'])
    def get_transactions():
        limit = int(request.args.get('limit', 100))
        user_id = request.args.get('user_id')
        
        transactions = app.config['transactions']
        if user_id:
            transactions = [t for t in transactions if t.get('user_id') == user_id]
        
        transactions = sorted(transactions, key=lambda x: x.get('timestamp', ''), reverse=True)[:limit]
        return jsonify({'success': True, 'count': len(transactions), 'transactions': transactions})
    
    @app.route('/api/add_transaction', methods=['POST'])
    def add_transaction():
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        transaction_id = f"TXN{uuid.uuid4().hex[:12].upper()}"
        user_id = session.get('user_id') or 'GUEST'
        
        transaction = {'transaction_id': transaction_id, 'user_id': user_id, 'account_number': data.get('account_number', ''), 'user_name': data.get('user_name', ''), 'amount': float(data.get('amount', 0)), 'transaction_type': data.get('transaction_type', 'Card'), 'location': data.get('location', 'Online'), 'card_present': data.get('card_present', True), 'timestamp': datetime.now().isoformat()}
        
        fraud_detector = app.config['fraud_detector']
        result = fraud_detector.analyze_transaction(transaction)
        
        transaction['is_fraud'] = result['is_fraud']
        transaction['fraud_probability'] = result['fraud_probability']
        transaction['risk_level'] = result['risk_level']
        transaction['reasons'] = result.get('reasons', [])
        
        app.config['transactions'].append(transaction)
        
        if len(app.config['transactions']) > 1000:
            app.config['transactions'] = app.config['transactions'][-1000:]
        
        if transaction['is_fraud']:
            alert = {'transaction_id': transaction['transaction_id'], 'user_id': transaction['user_id'], 'amount': transaction['amount'], 'alert_time': datetime.now().isoformat(), 'status': 'new', 'risk_level': transaction['risk_level'], 'reasons': transaction['reasons']}
            app.config['alerts'].append(alert)
            
            db = get_db()
            cursor = db.cursor()
            cursor.execute('SELECT * FROM verified_users WHERE user_id = ?', (transaction['user_id'],))
            verified_user = cursor.fetchone()
            
            if verified_user:
                mobile_number = verified_user['mobile_number']
                message = f"🚨 FRAUD ALERT: Suspicious transaction of ${transaction['amount']:.2f} detected (ID: {transaction['transaction_id']}). If this wasn't you, contact your bank immediately."
                simulate_send_sms(mobile_number, message)
                
                cursor.execute('INSERT INTO user_alerts (user_id, transaction_id, mobile_number, amount, alert_message) VALUES (?, ?, ?, ?, ?)', (transaction['user_id'], transaction['transaction_id'], mobile_number, transaction['amount'], message))
                db.commit()
        
        return jsonify({'success': True, 'transaction': transaction})
    
    @app.route('/api/generate-transaction', methods=['POST'])
    def generate_transaction():
        generator = app.config['transaction_generator']
        transaction = generator.generate_transaction()
        
        fraud_detector = app.config['fraud_detector']
        result = fraud_detector.analyze_transaction(transaction)
        
        transaction['is_fraud'] = result['is_fraud']
        transaction['fraud_probability'] = result['fraud_probability']
        transaction['risk_level'] = result['risk_level']
        
        app.config['transactions'].append(transaction)
        
        if transaction['is_fraud']:
            app.config['alerts'].append({'transaction_id': transaction['transaction_id'], 'amount': transaction['amount'], 'alert_time': datetime.now().isoformat(), 'status': 'new'})
        
        return jsonify({'success': True, 'transaction': transaction})
    
    @app.route('/api/alerts', methods=['GET'])
    def get_alerts():
        user_id = session.get('user_id') or request.args.get('user_id')
        
        alerts = sorted(app.config['alerts'], key=lambda x: x.get('alert_time', ''), reverse=True)[:50]
        
        if user_id:
            alerts = [a for a in alerts if a.get('user_id') == user_id]
        
        return jsonify({'success': True, 'count': len(alerts), 'alerts': alerts})
    
    @app.route('/api/stats', methods=['GET'])
    def get_stats():
        user_id = session.get('user_id') or request.args.get('user_id')
        
        transactions = app.config['transactions']
        
        if user_id:
            transactions = [t for t in transactions if t.get('user_id') == user_id]
        
        total = len(transactions)
        fraud_count = sum(1 for t in transactions if t.get('is_fraud'))
        
        return jsonify({'success': True, 'stats': {'total_transactions': total, 'fraud_transactions': fraud_count, 'normal_transactions': total - fraud_count, 'fraud_percentage': round(fraud_count / total * 100, 2) if total > 0 else 0, 'new_alerts': len([a for a in app.config['alerts'] if a.get('user_id') == user_id]) if user_id else len(app.config['alerts'])}})
    
    @app.route('/api/recent-transactions', methods=['GET'])
    def get_recent_transactions():
        user_id = session.get('user_id') or request.args.get('user_id')
        limit = int(request.args.get('limit', 20))
        
        transactions = app.config['transactions']
        
        if user_id:
            transactions = [t for t in transactions if t.get('user_id') == user_id]
        
        transactions = sorted(transactions, key=lambda x: x.get('timestamp', ''), reverse=True)[:limit]
        return jsonify({'success': True, 'transactions': transactions})
    
    @app.route('/api/start-stream', methods=['POST'])
    def start_stream():
        global running
        if running:
            return jsonify({'success': False, 'message': 'Stream already running'})
        
        running = True
        
        def generate_transactions_thread(app):
            while running:
                try:
                    generator = app.config['transaction_generator']
                    transaction = generator.generate_transaction()
                    
                    fraud_detector = app.config['fraud_detector']
                    result = fraud_detector.analyze_transaction(transaction)
                    
                    transaction['is_fraud'] = result['is_fraud']
                    transaction['fraud_probability'] = result['fraud_probability']
                    transaction['risk_level'] = result['risk_level']
                    transaction['reasons'] = result.get('reasons', [])
                    
                    app.config['transactions'].append(transaction)
                    
                    if len(app.config['transactions']) > 1000:
                        app.config['transactions'] = app.config['transactions'][-1000:]
                    
                    if transaction['is_fraud']:
                        alert = {'transaction_id': transaction['transaction_id'], 'user_id': transaction['user_id'], 'amount': transaction['amount'], 'timestamp': transaction['timestamp'], 'alert_time': datetime.now().isoformat(), 'status': 'new', 'risk_level': transaction['risk_level'], 'reasons': transaction['reasons']}
                        app.config['alerts'].append(alert)
                        
                        db = get_db()
                        cursor = db.cursor()
                        cursor.execute('SELECT * FROM verified_users WHERE user_id = ?', (transaction['user_id'],))
                        verified_user = cursor.fetchone()
                        
                        if verified_user:
                            mobile_number = verified_user['mobile_number']
                            message = f"🚨 FRAUD ALERT: Suspicious transaction of ${transaction['amount']:.2f} detected (ID: {transaction['transaction_id']}). If this wasn't you, contact your bank immediately."
                            simulate_send_sms(mobile_number, message)
                            
                            cursor.execute('INSERT INTO user_alerts (user_id, transaction_id, mobile_number, amount, alert_message) VALUES (?, ?, ?, ?, ?)', (transaction['user_id'], transaction['transaction_id'], mobile_number, transaction['amount'], message))
                            db.commit()
                        
                        logger.warning(f"🚨 FRAUD DETECTED: {transaction['transaction_id']} - ${transaction['amount']:.2f}")
                    
                    time.sleep(1.0 / config.TRANSACTIONS_PER_SECOND)
                    
                except Exception as e:
                    logger.error(f"Error generating transaction: {e}")
                    time.sleep(1)
        
        thread = threading.Thread(target=generate_transactions_thread, args=(app,))
        thread.daemon = True
        thread.start()
        
        return jsonify({'success': True, 'message': 'Transaction stream started'})
    
    @app.route('/api/stop-stream', methods=['POST'])
    def stop_stream():
        global running
        running = False
        return jsonify({'success': True, 'message': 'Transaction stream stopped'})
    
    @app.route('/api/stream-status', methods=['GET'])
    def stream_status():
        global running
        return jsonify({'success': True, 'running': running})
    
    @app.route('/api/attempt-call', methods=['POST'])
    def attempt_call():
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        caller_number = data.get('caller_number', '').strip()
        recipient_number = data.get('recipient_number', '').strip()
        user_id = session.get('user_id') or data.get('user_id')
        
        if not caller_number or not recipient_number:
            return jsonify({'success': False, 'error': 'Caller and recipient numbers required'}), 400
        
        caller_number = ''.join(filter(str.isdigit, caller_number))
        if not caller_number.startswith('+'):
            caller_number = '+1' + caller_number[-10:]
        
        recipient_number = ''.join(filter(str.isdigit, recipient_number))
        
        suspicious_result = check_suspicious_pattern(app, user_id or caller_number, recipient_number)
        
        if suspicious_result['is_suspicious']:
            activity = {'user_id': user_id or caller_number, 'user_number': caller_number, 'activity_type': 'SUSPICIOUS_CALL_PATTERN', 'description': suspicious_result['reason'], 'timestamp': datetime.now().isoformat(), 'alert_status': 'new'}
            app.config['suspicious_activities'].append(activity)
            
            db = get_db()
            cursor = db.cursor()
            cursor.execute('INSERT INTO suspicious_activities (user_id, user_number, activity_type, description, alert_status, sms_sent, email_sent) VALUES (?, ?, ?, ?, ?, ?, ?)', (activity['user_id'], activity['user_number'], activity['activity_type'], activity['description'], activity['alert_status'], 1, 1))
            db.commit()
            
            sms_message = f"🚨 SUSPICIOUS ACTIVITY: {suspicious_result['reason']}. Your call to {recipient_number} has been flagged."
            simulate_send_sms(caller_number, sms_message)
            
            email_subject = "Fraud Alert: Suspicious Call Activity Detected"
            email_body = f"Suspicious call activity detected:\n\nUser Number: {caller_number}\nRecipient Number: {recipient_number}\nActivity: {suspicious_result['reason']}\nTime: {datetime.now().isoformat()}\n\nPlease review this activity immediately."
            send_email_alert(config.ADMIN_EMAIL, email_subject, email_body)
            
            return jsonify({'success': False, 'is_suspicious': True, 'message': 'Call blocked - suspicious activity detected', 'reason': suspicious_result['reason'], 'alert_sent': True})
        
        call_otp = generate_otp()
        expires_at = datetime.now() + timedelta(seconds=config.CALL_OTP_EXPIRY_SECONDS)
        
        app.config['call_otp_store'][caller_number] = {'otp': call_otp, 'recipient': recipient_number, 'expires_at': expires_at, 'user_id': user_id}
        
        sms_message = f"Your verification code for calling {recipient_number} is: {call_otp}. This code expires in 2 minutes."
        simulate_send_sms(caller_number, sms_message)
        
        logger.info(f"Call OTP sent to {caller_number} for calling {recipient_number}: {call_otp}")
        
        return jsonify({'success': True, 'requires_verification': True, 'message': 'OTP sent to your mobile number for call verification', 'expires_in': config.CALL_OTP_EXPIRY_SECONDS})
    
    @app.route('/api/verify-call-otp', methods=['POST'])
    def verify_call_otp():
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        caller_number = data.get('caller_number', '').strip()
        otp_code = data.get('otp_code', '').strip()
        
        if not caller_number or not otp_code:
            return jsonify({'success': False, 'error': 'Caller number and OTP required'}), 400
        
        caller_number = ''.join(filter(str.isdigit, caller_number))
        if not caller_number.startswith('+'):
            caller_number = '+1' + caller_number[-10:]
        
        otp_record = app.config['call_otp_store'].get(caller_number)
        
        if not otp_record:
            return jsonify({'success': False, 'error': 'No OTP found. Please initiate call first.'}), 400
        
        if otp_record['otp'] != otp_code:
            return jsonify({'success': False, 'error': 'Invalid OTP'}), 400
        
        if datetime.now() > otp_record['expires_at']:
            return jsonify({'success': False, 'error': 'OTP expired'}), 400
        
        call_log = {'caller_number': caller_number, 'recipient_number': otp_record['recipient'], 'call_time': datetime.now().isoformat(), 'status': 'completed', 'user_id': otp_record['user_id'], 'otp_verified': True}
        app.config['call_logs'].append(call_log)
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('INSERT INTO call_logs (caller_number, recipient_number, status, user_id, otp_verified) VALUES (?, ?, ?, ?, ?)', (caller_number, otp_record['recipient'], 'completed', otp_record['user_id'], 1))
        db.commit()
        
        del app.config['call_otp_store'][caller_number]
        
        logger.info(f"Call verified: {caller_number} -> {otp_record['recipient']}")
        
        return jsonify({'success': True, 'message': 'Call verified successfully', 'recipient_number': otp_record['recipient']})
    
    @app.route('/api/suspicious-activities', methods=['GET'])
    def get_suspicious_activities():
        limit = int(request.args.get('limit', 50))
        
        activities = sorted(app.config['suspicious_activities'], key=lambda x: x.get('timestamp', ''), reverse=True)[:limit]
        
        return jsonify({'success': True, 'count': len(activities), 'activities': activities})
    
    @app.route('/api/update-suspicious-status', methods=['POST'])
    def update_suspicious_status():
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        activity_id = data.get('id')
        new_status = data.get('status')
        
        if not activity_id or not new_status:
            return jsonify({'success': False, 'error': 'ID and status required'}), 400
        
        for activity in app.config['suspicious_activities']:
            if activity.get('id') == activity_id:
                activity['alert_status'] = new_status
                break
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('UPDATE suspicious_activities SET alert_status = ? WHERE id = ?', (new_status, activity_id))
        db.commit()
        
        return jsonify({'success': True, 'status': new_status})
    
    @app.route('/api/admin/stats', methods=['GET'])
    def admin_stats():
        total_transactions = len(app.config['transactions'])
        fraud_transactions = sum(1 for t in app.config['transactions'] if t.get('is_fraud'))
        total_alerts = len(app.config['alerts'])
        suspicious_activities_count = len(app.config['suspicious_activities'])
        call_logs_count = len(app.config['call_logs'])
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT COUNT(*) as count FROM verified_users')
        verified_users_count = cursor.fetchone()['count']
        
        return jsonify({'success': True, 'stats': {'total_transactions': total_transactions, 'fraud_transactions': fraud_transactions, 'fraud_percentage': round(fraud_transactions / total_transactions * 100, 2) if total_transactions > 0 else 0, 'total_alerts': total_alerts, 'suspicious_activities': suspicious_activities_count, 'call_logs': call_logs_count, 'verified_users': verified_users_count, 'timestamp': datetime.now().isoformat()}})
    
    @app.route('/api/admin/all-activities', methods=['GET'])
    def admin_all_activities():
        limit = int(request.args.get('limit', 100))
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM suspicious_activities ORDER BY timestamp DESC LIMIT ?', (limit,))
        
        activities = []
        for row in cursor.fetchall():
            activities.append({'id': row['id'], 'user_id': row['user_id'], 'user_number': row['user_number'], 'activity_type': row['activity_type'], 'description': row['description'], 'timestamp': row['timestamp'], 'alert_status': row['alert_status'], 'sms_sent': bool(row['sms_sent']), 'email_sent': bool(row['email_sent'])})
        
        return jsonify({'success': True, 'count': len(activities), 'activities': activities})


def check_suspicious_pattern(app, user_id, recipient_number):
    now = datetime.now()
    time_window = timedelta(minutes=config.SUSPICIOUS_TIME_WINDOW_MINUTES)
    
    recent_calls = [c for c in app.config['call_logs'] if c.get('user_id') == user_id or c.get('caller_number', '').endswith(str(user_id)[-4:])]
    
    unknown_calls = [c for c in recent_calls if c.get('recipient_number') != recipient_number and now - datetime.fromisoformat(c.get('call_time', now.isoformat())) < time_window]
    
    if len(unknown_calls) >= config.MAX_UNKNOWN_CALLS_PER_HOUR:
        return {'is_suspicious': True, 'reason': f'Unusual calling pattern detected: {len(unknown_calls)} calls to different numbers in the last hour'}
    
    same_number_calls = [c for c in recent_calls if c.get('recipient_number') == recipient_number and now - datetime.fromisoformat(c.get('call_time', now.isoformat())) < time_window]
    
    if len(same_number_calls) >= 5:
        return {'is_suspicious': True, 'reason': f'Repeated calls to unknown number ({len(same_number_calls)} times in the last hour)'}
    
    return {'is_suspicious': False}


def main():
    app = create_app()
    logger.info(f"Starting API on {config.API_HOST}:{config.API_PORT}")
    logger.info("API Endpoints:")
    logger.info("  - GET/POST standard endpoints")
    logger.info("  - POST /api/attempt-call : Attempt call with OTP verification")
    logger.info("  - POST /api/verify-call-otp : Verify call OTP")
    logger.info("  - GET /api/suspicious-activities : Get suspicious activities")
    logger.info("  - GET /api/admin/stats : Admin dashboard stats")
    logger.info("  - GET /api/admin/all-activities : Admin all activities")
    app.run(host=config.API_HOST, port=config.API_PORT, debug=config.API_DEBUG, threaded=True)


if __name__ == "__main__":
    main()

