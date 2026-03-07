"""
Flask Backend API - Real-Time Fraud Detection System
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
import csv
import io
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, session, g
from flask_cors import CORS
from werkzeug.utils import secure_filename

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from models.fraud_detector import FraudDetector
from streaming.transaction_generator import TransactionGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# Global state for stream management
running = False
stream_thread = None

DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fraud_detection.db')
ALLOWED_EXTENSIONS = {'csv'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT UNIQUE NOT NULL,
        username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS verified_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT UNIQUE NOT NULL,
        username TEXT, mobile_number TEXT UNIQUE NOT NULL,
        verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS otp_store (
        id INTEGER PRIMARY KEY AUTOINCREMENT, mobile_number TEXT NOT NULL,
        otp_code TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL, verified BOOLEAN DEFAULT 0, user_id TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_id TEXT UNIQUE NOT NULL,
        user_id TEXT, account_number TEXT, transaction_date TEXT, amount REAL NOT NULL,
        transaction_type TEXT, receiver_account TEXT, description TEXT, location TEXT,
        is_fraud BOOLEAN DEFAULT 0, risk_level TEXT DEFAULT 'LOW',
        fraud_probability REAL DEFAULT 0.0, fraud_reasons TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, transaction_id TEXT NOT NULL, user_id TEXT,
        amount REAL NOT NULL, alert_type TEXT, alert_message TEXT, risk_level TEXT,
        sent_sms BOOLEAN DEFAULT 0, sent_email BOOLEAN DEFAULT 0,
        alert_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP, status TEXT DEFAULT 'new')''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS bank_statements (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, filename TEXT,
        upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_transactions INTEGER DEFAULT 0, total_amount REAL DEFAULT 0,
        suspicious_count INTEGER DEFAULT 0)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS activity_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, activity_type TEXT,
        description TEXT, ip_address TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    db.commit()
    db.close()
    logger.info("Database initialized successfully")


def generate_otp():
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])


def is_otp_expired(expires_at):
    try:
        expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        return datetime.now() > expires_datetime
    except:
        return True


def simulate_send_sms(mobile_number, message):
    if config.SMS_SIMULATION_LOG:
        logger.info(f"📱 [SMS] To: {mobile_number} | Message: {message}")
    return True


def send_email_alert(recipient_email, subject, message_body):
    if config.EMAIL_SIMULATION:
        logger.info(f"📧 [EMAIL] To: {recipient_email} | Subject: {subject}")
    return True


def analyze_transaction_risk(transaction):
    reasons = []
    risk_score = 0.0
    amount = float(transaction.get('amount', 0))
    
    if amount >= 50000:
        reasons.append(f"High amount: ₹{amount:,.2f}")
        risk_score += 0.4
    elif amount >= 25000:
        reasons.append(f"Medium-high amount: ₹{amount:,.2f}")
        risk_score += 0.2
    
    receiver = transaction.get('receiver_account', '')
    if receiver and (receiver.startswith('UNKNOWN') or receiver == ''):
        reasons.append("Transfer to unknown account")
        risk_score += 0.3
    
    txn_type = transaction.get('transaction_type', '').upper()
    if txn_type in ['INTERNATIONAL', 'WIRE_TRANSFER']:
        reasons.append(f"Unusual type: {txn_type}")
        risk_score += 0.2
    
    if risk_score >= 0.7:
        risk_level = 'HIGH'
    elif risk_score >= 0.4:
        risk_level = 'MEDIUM'
    else:
        risk_level = 'LOW'
    
    is_fraud = risk_score >= 0.5
    
    return {'is_fraud': is_fraud, 'risk_level': risk_level,
            'fraud_probability': min(risk_score, 1.0), 'reasons': reasons}


def check_duplicate_transactions(user_id, amount, time_window_minutes=5):
    db = get_db()
    cursor = db.cursor()
    cutoff_time = datetime.now() - timedelta(minutes=time_window_minutes)
    cursor.execute('''SELECT COUNT(*) as count FROM transactions 
        WHERE user_id = ? AND amount = ? AND timestamp > ?''',
        (user_id, amount, cutoff_time.isoformat()))
    result = cursor.fetchone()
    return result['count'] if result else 0


def log_activity(user_id, activity_type, description):
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''INSERT INTO activity_logs (user_id, activity_type, description) VALUES (?, ?, ?)''',
            (user_id, activity_type, description))
        db.commit()
    except:
        pass


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
    
    register_routes(app)
    return app


def register_routes(app):
    @app.route('/')
    def index():
        return jsonify({'status': 'running', 'service': 'Fraud Detection API', 'version': '5.0.0', 'timestamp': datetime.now().isoformat()})
    
    @app.route('/api/')
    def api_root():
        return jsonify({'status': 'running', 'service': 'Fraud Detection API', 'version': '5.0.0', 'timestamp': datetime.now().isoformat(),
            'endpoints': {'health': '/api/health', 'auth': '/api/register, /api/login',
                'transactions': '/api/transactions, /api/analyze', 'upload': '/api/upload-statement',
                'stats': '/api/stats', 'alerts': '/api/alerts', 'analytics': '/api/analytics',
                'stream': '/api/stream-status, /api/start-stream, /api/stop-stream',
                'verification': '/api/send-otp, /api/verify-otp, /api/current-user'}})
    
    @app.route('/api/health', methods=['GET'])
    def health_check():
        global running
        return jsonify({'status': 'healthy', 'service': 'Fraud Detection API',
            'ml_model': 'loaded' if app.config['fraud_detector'].initialized else 'rule-based',
            'stream_running': running,
            'transactions_count': len(app.config['transactions']),
            'alerts_count': len(app.config['alerts']), 
            'timestamp': datetime.now().isoformat()})
    
    # AUTHENTICATION
    @app.route('/api/register', methods=['POST'])
    def register():
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '')
        email = data.get('email', '').strip()
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password required'}), 400
        
        users = app.config['users']
        if any(u['username'] == username for u in users):
            return jsonify({'success': False, 'error': 'Username exists'}), 400
        
        user_id = str(uuid.uuid4())
        user = {'id': user_id, 'username': username, 'password_hash': hash_password(password),
                'email': email, 'created_at': datetime.now().isoformat()}
        users.append(user)
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('INSERT INTO users (user_id, username, password_hash, email) VALUES (?, ?, ?, ?)',
            (user_id, username, hash_password(password), email))
        db.commit()
        log_activity(user_id, 'REGISTER', f'User {username} registered')
        
        return jsonify({'success': True, 'message': 'Registered successfully', 'user': {'id': user_id, 'username': username}}), 201
    
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
        log_activity(user['id'], 'LOGIN', f'User {username} logged in')
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM verified_users WHERE user_id = ?', (user['id'],))
        verified_user = cursor.fetchone()
        
        is_verified = verified_user is not None
        mobile_number = verified_user['mobile_number'] if verified_user else None
        
        return jsonify({'success': True, 'user': {'id': user['id'], 'username': user['username'], 'email': user.get('email')},
            'is_verified': is_verified, 'mobile_number': mobile_number})
    
    @app.route('/api/logout', methods=['POST'])
    def logout():
        user_id = session.get('user_id')
        if user_id:
            log_activity(user_id, 'LOGOUT', 'User logged out')
        session.clear()
        return jsonify({'success': True})
    
    @app.route('/api/current-user', methods=['GET'])
    def current_user():
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
        
        return jsonify({'success': True, 'logged_in': True, 'username': username, 'user_id': user_id,
            'email': email, 'is_verified': is_verified, 'mobile_number': mobile_number})
    
    # OTP VERIFICATION
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
        expires_at = datetime.now() + timedelta(seconds=60)
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('DELETE FROM otp_store WHERE mobile_number = ? AND verified = 0', (mobile_number,))
        cursor.execute('INSERT INTO otp_store (mobile_number, otp_code, expires_at, user_id) VALUES (?, ?, ?, ?)',
            (mobile_number, otp_code, expires_at.isoformat(), user_id))
        db.commit()
        
        message = f"Your verification code is: {otp_code}. This code expires in 60 seconds."
        simulate_send_sms(mobile_number, message)
        logger.info(f"OTP sent to {mobile_number}: {otp_code}")
        
        return jsonify({'success': True, 'message': 'OTP sent successfully', 'expires_in': 60, 'otp_code': otp_code})
    
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
        cursor.execute('''SELECT * FROM otp_store WHERE mobile_number = ? AND otp_code = ? AND verified = 0
            ORDER BY created_at DESC LIMIT 1''', (mobile_number, otp_code))
        otp_record = cursor.fetchone()
        
        if not otp_record:
            return jsonify({'success': False, 'error': 'Invalid OTP'}), 400
        
        if is_otp_expired(otp_record['expires_at']):
            return jsonify({'success': False, 'error': 'OTP expired'}), 400
        
        cursor.execute('UPDATE otp_store SET verified = 1 WHERE id = ?', (otp_record['id'],))
        
        username = session.get('username') or f'User_{mobile_number[-4:]}'
        cursor.execute('''INSERT OR REPLACE INTO verified_users (user_id, username, mobile_number, verified_at)
            VALUES (?, ?, ?, ?)''', (user_id or str(uuid.uuid4()), username, mobile_number, datetime.now().isoformat()))
        db.commit()
        
        simulate_send_sms(mobile_number, f"Your mobile number {mobile_number} has been verified.")
        log_activity(user_id, 'OTP_VERIFIED', f'Mobile {mobile_number} verified')
        
        return jsonify({'success': True, 'message': 'Mobile number verified successfully', 'mobile_number': mobile_number})
    
    # BANK STATEMENT UPLOAD
    @app.route('/api/upload-statement', methods=['POST'])
    def upload_bank_statement():
        user_id = session.get('user_id') or request.form.get('user_id', 'GUEST')
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Only CSV files are allowed'}), 400
        
        try:
            content = file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
            
            transactions_analyzed = 0
            suspicious_count = 0
            total_amount = 0.0
            analyzed_transactions = []
            
            db = get_db()
            cursor = db.cursor()
            
            for row in csv_reader:
                transaction = {
                    'transaction_id': f"TXN{uuid.uuid4().hex[:12].upper()}",
                    'user_id': user_id,
                    'transaction_date': row.get('date', row.get('Date', row.get('Transaction Date', datetime.now().isoformat()))),
                    'amount': float(row.get('amount', row.get('Amount', row.get('Debit', row.get('Credit', 0))))),
                    'transaction_type': row.get('type', row.get('Type', row.get('Transaction Type', 'TRANSFER'))),
                    'receiver_account': row.get('receiver', row.get('Receiver', row.get('To', ''))),
                    'description': row.get('description', row.get('Description', row.get('Narration', ''))),
                    'location': row.get('location', row.get('Location', 'Online'))
                }
                
                amount = transaction['amount']
                if amount <= 0:
                    continue
                
                total_amount += amount
                
                duplicate_count = check_duplicate_transactions(user_id, amount, time_window_minutes=5)
                if duplicate_count > 0:
                    transaction['fraud_reasons'] = f"Repeated transaction ({duplicate_count} times in 5 minutes)"
                    suspicious_count += 1
                
                analysis = analyze_transaction_risk(transaction)
                transaction['is_fraud'] = analysis['is_fraud']
                transaction['risk_level'] = analysis['risk_level']
                transaction['fraud_probability'] = analysis['fraud_probability']
                transaction['reasons'] = analysis['reasons']
                
                if analysis['is_fraud']:
                    suspicious_count += 1
                    alert_message = f"Suspicious transaction detected: ₹{amount:,.2f}"
                    if analysis['reasons']:
                        alert_message += f". Reasons: {', '.join(analysis['reasons'])}"
                    
                    cursor.execute('''INSERT INTO alerts (transaction_id, user_id, amount, alert_type, alert_message, risk_level, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''', (transaction['transaction_id'], user_id, amount, 'SUSPICIOUS', alert_message, analysis['risk_level'], 'new'))
                    
                    cursor.execute('SELECT * FROM verified_users WHERE user_id = ?', (user_id,))
                    verified = cursor.fetchone()
                    if verified:
                        simulate_send_sms(verified['mobile_number'], alert_message)
                        send_email_alert(config.ADMIN_EMAIL, "Fraud Alert", alert_message)
                
                cursor.execute('''INSERT INTO transactions (transaction_id, user_id, transaction_date, amount, transaction_type,
                    receiver_account, description, location, is_fraud, risk_level, fraud_probability, fraud_reasons)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                    (transaction['transaction_id'], user_id, transaction['transaction_date'], amount, transaction['transaction_type'],
                     transaction['receiver_account'], transaction['description'], transaction['location'], analysis['is_fraud'],
                     analysis['risk_level'], analysis['fraud_probability'], ','.join(analysis['reasons']) if analysis['reasons'] else ''))
                
                transactions_analyzed += 1
                analyzed_transactions.append(transaction)
            
            db.commit()
            
            cursor.execute('''INSERT INTO bank_statements (user_id, filename, total_transactions, total_amount, suspicious_count)
                VALUES (?, ?, ?, ?, ?)''',
                (user_id, secure_filename(file.filename), transactions_analyzed, total_amount, suspicious_count))
            db.commit()
            log_activity(user_id, 'UPLOAD', f'Uploaded bank statement: {file.filename}')
            
            return jsonify({'success': True, 'message': f'Successfully analyzed {transactions_analyzed} transactions',
                'results': {'total_transactions': transactions_analyzed, 'total_amount': total_amount,
                    'suspicious_transactions': suspicious_count, 'transactions': analyzed_transactions[-20:]}})
            
        except Exception as e:
            logger.error(f"Error processing bank statement: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # TRANSACTIONS
    @app.route('/api/transactions', methods=['GET'])
    def get_transactions():
        user_id = session.get('user_id') or request.args.get('user_id')
        limit = int(request.args.get('limit', 50))
        risk_level = request.args.get('risk_level')
        
        db = get_db()
        cursor = db.cursor()
        
        if user_id:
            if risk_level:
                cursor.execute('SELECT * FROM transactions WHERE user_id = ? AND risk_level = ? ORDER BY timestamp DESC LIMIT ?', (user_id, risk_level, limit))
            else:
                cursor.execute('SELECT * FROM transactions WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?', (user_id, limit))
        else:
            if risk_level:
                cursor.execute('SELECT * FROM transactions WHERE risk_level = ? ORDER BY timestamp DESC LIMIT ?', (risk_level, limit))
            else:
                cursor.execute('SELECT * FROM transactions ORDER BY timestamp DESC LIMIT ?', (limit,))
        
        transactions = []
        for row in cursor.fetchall():
            transactions.append({'id': row['id'], 'transaction_id': row['transaction_id'], 'user_id': row['user_id'],
                'amount': row['amount'], 'transaction_type': row['transaction_type'], 'receiver_account': row['receiver_account'],
                'description': row['description'], 'location': row['location'], 'is_fraud': bool(row['is_fraud']),
                'risk_level': row['risk_level'], 'fraud_probability': row['fraud_probability'],
                'fraud_reasons': row['fraud_reasons'], 'timestamp': row['timestamp']})
        
        return jsonify({'success': True, 'count': len(transactions), 'transactions': transactions})
    
    @app.route('/api/analyze', methods=['POST'])
    def analyze_transaction():
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        user_id = session.get('user_id') or data.get('user_id', 'GUEST')
        
        transaction = {'transaction_id': f"TXN{uuid.uuid4().hex[:12].upper()}", 'user_id': user_id,
            'amount': float(data.get('amount', 0)), 'transaction_type': data.get('transaction_type', 'TRANSFER'),
            'receiver_account': data.get('receiver_account', ''), 'description': data.get('description', ''),
            'location': data.get('location', 'Online')}
        
        if transaction['amount'] <= 0:
            return jsonify({'success': False, 'error': 'Invalid amount'}), 400
        
        duplicate_count = check_duplicate_transactions(user_id, transaction['amount'], time_window_minutes=5)
        if duplicate_count > 0:
            transaction['fraud_reasons'] = f"Repeated transaction ({duplicate_count} times in 5 minutes)"
        
        analysis = analyze_transaction_risk(transaction)
        transaction['is_fraud'] = analysis['is_fraud']
        transaction['risk_level'] = analysis['risk_level']
        transaction['fraud_probability'] = analysis['fraud_probability']
        transaction['reasons'] = analysis['reasons']
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''INSERT INTO transactions (transaction_id, user_id, amount, transaction_type, receiver_account,
            description, is_fraud, risk_level, fraud_probability, fraud_reasons)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (transaction['transaction_id'], user_id, transaction['amount'], transaction['transaction_type'],
             transaction['receiver_account'], transaction['description'], analysis['is_fraud'], analysis['risk_level'],
             analysis['fraud_probability'], ','.join(analysis['reasons']) if analysis['reasons'] else ''))
        
        if analysis['is_fraud']:
            alert_message = f"Suspicious transaction detected: ₹{transaction['amount']:,.2f}"
            if analysis['reasons']:
                alert_message += f". Reasons: {', '.join(analysis['reasons'])}"
            
            cursor.execute('''INSERT INTO alerts (transaction_id, user_id, amount, alert_type, alert_message, risk_level, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (transaction['transaction_id'], user_id, transaction['amount'], 'SUSPICIOUS', alert_message, analysis['risk_level'], 'new'))
            
            cursor.execute('SELECT * FROM verified_users WHERE user_id = ?', (user_id,))
            verified = cursor.fetchone()
            if verified:
                simulate_send_sms(verified['mobile_number'], alert_message)
                send_email_alert(config.ADMIN_EMAIL, "Fraud Alert", alert_message)
        
        db.commit()
        
        return jsonify({'success': True, 'transaction': transaction, 'analysis': analysis})
    
    # ALERTS
    @app.route('/api/alerts', methods=['GET'])
    def get_alerts():
        user_id = session.get('user_id') or request.args.get('user_id')
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        
        db = get_db()
        cursor = db.cursor()
        
        if user_id:
            if status:
                cursor.execute('SELECT * FROM alerts WHERE user_id = ? AND status = ? ORDER BY alert_time DESC LIMIT ?', (user_id, status, limit))
            else:
                cursor.execute('SELECT * FROM alerts WHERE user_id = ? ORDER BY alert_time DESC LIMIT ?', (user_id, limit))
        else:
            if status:
                cursor.execute('SELECT * FROM alerts WHERE status = ? ORDER BY alert_time DESC LIMIT ?', (status, limit))
            else:
                cursor.execute('SELECT * FROM alerts ORDER BY alert_time DESC LIMIT ?', (limit,))
        
        alerts = []
        for row in cursor.fetchall():
            alerts.append({'id': row['id'], 'transaction_id': row['transaction_id'], 'user_id': row['user_id'],
                'amount': row['amount'], 'alert_type': row['alert_type'], 'alert_message': row['alert_message'],
                'risk_level': row['risk_level'], 'sent_sms': bool(row['sent_sms']), 'sent_email': bool(row['sent_email']),
                'alert_time': row['alert_time'], 'status': row['status']})
        
        return jsonify({'success': True, 'count': len(alerts), 'alerts': alerts})
    
    @app.route('/api/alerts/<int:alert_id>', methods=['PUT'])
    def update_alert(alert_id):
        data = request.get_json()
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'success': False, 'error': 'Status required'}), 400
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute('UPDATE alerts SET status = ? WHERE id = ?', (new_status, alert_id))
        db.commit()
        
        return jsonify({'success': True, 'status': new_status})
    
    # STATISTICS & ANALYTICS
    @app.route('/api/stats', methods=['GET'])
    def get_stats():
        user_id = session.get('user_id') or request.args.get('user_id')
        
        db = get_db()
        cursor = db.cursor()
        
        if user_id:
            cursor.execute('SELECT COUNT(*) as count FROM transactions WHERE user_id = ?', (user_id,))
            total_txn = cursor.fetchone()['count']
            cursor.execute('SELECT COUNT(*) as count FROM transactions WHERE user_id = ? AND is_fraud = 1', (user_id,))
            fraud_txn = cursor.fetchone()['count']
            cursor.execute('SELECT SUM(amount) as total FROM transactions WHERE user_id = ?', (user_id,))
            total_amount = cursor.fetchone()['total'] or 0
            cursor.execute('SELECT COUNT(*) as count FROM alerts WHERE user_id = ? AND status = ?', (user_id, 'new'))
            new_alerts = cursor.fetchone()['count']
            cursor.execute('SELECT COUNT(*) as count FROM alerts WHERE user_id = ?', (user_id,))
            total_alerts = cursor.fetchone()['count']
        else:
            cursor.execute('SELECT COUNT(*) as count FROM transactions')
            total_txn = cursor.fetchone()['count']
            cursor.execute('SELECT COUNT(*) as count FROM transactions WHERE is_fraud = 1')
            fraud_txn = cursor.fetchone()['count']
            cursor.execute('SELECT SUM(amount) as total FROM transactions')
            total_amount = cursor.fetchone()['total'] or 0
            cursor.execute('SELECT COUNT(*) as count FROM alerts WHERE status = ?', ('new',))
            new_alerts = cursor.fetchone()['count']
            cursor.execute('SELECT COUNT(*) as count FROM alerts')
            total_alerts = cursor.fetchone()['count']
        
        cursor.execute('SELECT risk_level, COUNT(*) as count FROM transactions GROUP BY risk_level')
        risk_distribution = {}
        for row in cursor.fetchall():
            risk_distribution[row['risk_level']] = row['count']
        
        return jsonify({'success': True, 'stats': {'total_transactions': total_txn, 'fraud_transactions': fraud_txn,
            'normal_transactions': total_txn - fraud_txn,
            'fraud_percentage': round(fraud_txn / total_txn * 100, 2) if total_txn > 0 else 0,
            'total_amount': round(total_amount, 2), 'total_alerts': total_alerts, 'new_alerts': new_alerts,
            'risk_distribution': risk_distribution}})
    
    @app.route('/api/analytics', methods=['GET'])
    def get_analytics():
        user_id = session.get('user_id') or request.args.get('user_id')
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''SELECT transaction_type, COUNT(*) as count, SUM(amount) as total
            FROM transactions WHERE user_id = ? OR user_id IS NULL GROUP BY transaction_type''',
            (user_id if user_id else None,))
        type_data = [{'type': row['transaction_type'], 'count': row['count'], 'total': row['total']} for row in cursor.fetchall()]
        
        cursor.execute('''SELECT DATE(timestamp) as date, COUNT(*) as total, SUM(is_fraud) as fraud_count
            FROM transactions WHERE user_id = ? AND timestamp > datetime('now', '-7 days')
            GROUP BY DATE(timestamp) ORDER BY date''', (user_id if user_id else None,))
        daily_data = [{'date': row['date'], 'total_transactions': row['total'], 'fraud_transactions': row['fraud_count']} for row in cursor.fetchall()]
        
        cursor.execute('''SELECT * FROM transactions WHERE is_fraud = 1 AND (user_id = ? OR user_id IS NULL)
            ORDER BY fraud_probability DESC LIMIT 10''', (user_id if user_id else None,))
        suspicious = [{'transaction_id': row['transaction_id'], 'amount': row['amount'], 'risk_level': row['risk_level'],
            'fraud_reasons': row['fraud_reasons'], 'timestamp': row['timestamp']} for row in cursor.fetchall()]
        
        cursor.execute('''SELECT * FROM activity_logs WHERE user_id = ? OR user_id IS NULL
            ORDER BY timestamp DESC LIMIT 20''', (user_id if user_id else None,))
        activities = [{'type': row['activity_type'], 'description': row['description'], 'timestamp': row['timestamp']} for row in cursor.fetchall()]
        
        return jsonify({'success': True, 'analytics': {'by_type': type_data, 'daily': daily_data, 'suspicious': suspicious, 'recent_activity': activities}})
    
    # REAL-TIME STREAM
    @app.route('/api/start-stream', methods=['POST'])
    def start_stream():
        global running, stream_thread
        
        if running:
            return jsonify({'success': True, 'message': 'Stream already running', 'running': True})
        
        running = True
        
        def generate_transactions_thread(app):
            with app.app_context():
                while running:
                    try:
                        generator = app.config['transaction_generator']
                        transaction = generator.generate_transaction()
                        
                        analysis = analyze_transaction_risk(transaction)
                        transaction['is_fraud'] = analysis['is_fraud']
                        transaction['risk_level'] = analysis['risk_level']
                        transaction['fraud_probability'] = analysis['fraud_probability']
                        transaction['reasons'] = analysis['reasons']
                        
                        db = get_db()
                        cursor = db.cursor()
                        cursor.execute('''INSERT INTO transactions (transaction_id, user_id, amount, transaction_type,
                            receiver_account, description, location, is_fraud, risk_level, fraud_probability, fraud_reasons)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                            (transaction['transaction_id'], transaction['user_id'], transaction['amount'],
                             transaction.get('merchant', 'ONLINE'), transaction.get('receiver_account', 'N/A'),
                             transaction.get('description', ''), transaction.get('location', 'Online'),
                             analysis['is_fraud'], analysis['risk_level'], analysis['fraud_probability'],
                             ','.join(analysis['reasons']) if analysis['reasons'] else ''))
                        db.commit()
                        
                        app.config['transactions'].append(transaction)
                        if len(app.config['transactions']) > 1000:
                            app.config['transactions'] = app.config['transactions'][-1000:]
                        
                        if transaction['is_fraud']:
                            alert = {'transaction_id': transaction['transaction_id'], 'amount': transaction['amount'],
                                'risk_level': transaction['risk_level'], 'alert_time': datetime.now().isoformat(), 'status': 'new'}
                            app.config['alerts'].append(alert)
                            
                            alert_message = f"Suspicious transaction: ${transaction['amount']:.2f}"
                            if analysis['reasons']:
                                alert_message += f". Reasons: {', '.join(analysis['reasons'])}"
                            
                            cursor.execute('''INSERT INTO alerts (transaction_id, user_id, amount, alert_type, alert_message, risk_level, status)
                                VALUES (?, ?, ?, ?, ?, ?, ?)''',
                                (transaction['transaction_id'], transaction['user_id'], transaction['amount'],
                                 'SUSPICIOUS', alert_message, analysis['risk_level'], 'new'))
                            db.commit()
                            
                            cursor.execute('SELECT * FROM verified_users WHERE user_id = ?', (transaction['user_id'],))
                            verified = cursor.fetchone()
                            if verified:
                                message = f"🚨 FRAUD ALERT: Suspicious transaction of ${transaction['amount']:.2f}"
                                simulate_send_sms(verified['mobile_number'], message)
                            
                            logger.warning(f"🚨 FRAUD DETECTED: {transaction['transaction_id']} - ${transaction['amount']:.2f}")
                        
                        time.sleep(1.0 / config.TRANSACTIONS_PER_SECOND)
                        
                    except Exception as e:
                        logger.error(f"Error generating transaction: {e}")
                        time.sleep(1)
        
        stream_thread = threading.Thread(target=generate_transactions_thread, args=(app,))
        stream_thread.daemon = True
        stream_thread.start()
        
        return jsonify({'success': True, 'message': 'Transaction stream started', 'running': True})
    
    @app.route('/api/stop-stream', methods=['POST'])
    def stop_stream():
        global running
        running = False
        return jsonify({'success': True, 'message': 'Transaction stream stopped', 'running': False})
    
    @app.route('/api/stream-status', methods=['GET'])
    def stream_status():
        global running
        return jsonify({'success': True, 'running': running})


def main():
    app = create_app()
    logger.info(f"Starting API on {config.API_HOST}:{config.API_PORT}")
    logger.info("Fraud Detection System v5.0.0")
    app.run(host=config.API_HOST, port=config.API_PORT, debug=config.API_DEBUG, threaded=True)


if __name__ == "__main__":
    main()

