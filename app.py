#!/usr/bin/env python3

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from admin_data import admin_db
from searched_usernames import searched_username_manager

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'super-secret-key-change-this')

app.config.update(
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='None',
    PERMANENT_SESSION_LIFETIME=1800
)

csrf = CSRFProtect(app)

CORS(app, resources={
    r'/*': {
        'origins': '*',
        'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
        'allow_headers': ['Content-Type', 'Authorization', 'X-Requested-With']
    }
})

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['TEMPLATES_AUTO_RELOAD'] = True


@app.before_request
def preflight():
    if request.method == "OPTIONS":
        response = app.make_response("")
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "*")
        response.headers.add("Access-Control-Allow-Methods", "*")
        return response


ADMIN_CREDENTIALS = {
    'rxprime': os.environ.get('ADMIN_PASSWORD_HASH_1', generate_password_hash('rxprime'))
}


class TelegramUserSearch:
    def search_public_info(self, username):
        if username.startswith('@'):
            username = username[1:]

        demo_users = admin_db.get_usernames()
        username_lower = username.lower()

        for u in demo_users:
            if u['active'] and u['username'].lower() == username_lower:
                return {
                    "success": True,
                    "user_data": {
                        "username": u['username'],
                        "mobile_number": u['mobile_number'],
                        "mobile_details": u['mobile_details']
                    }
                }

        return {"success": False, "error": "No details available in database"}


searcher = TelegramUserSearch()


@app.route('/')
def home():
    if not session.get('authenticated'):
        return redirect(url_for('login_page'))
    return redirect(url_for('dashboard'))


@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/signup', methods=['POST'])
@csrf.exempt
def signup():
    data = request.get_json()
    name = data.get('name', '').strip()

    if len(name) < 2:
        return jsonify({'success': False, 'error': 'Enter a valid name'})

    user = admin_db.create_user(name)
    return jsonify({
        'success': True,
        'hash_code': user['hash_code'],
        'name': user['name']
    })


@app.route('/login', methods=['POST'])
@csrf.exempt
def login():
    data = request.get_json()
    hash_code = data.get('hash_code', '').strip()

    user = admin_db.get_user_by_hash(hash_code)
    if not user:
        return jsonify({'success': False, 'error': 'Invalid hash code'})

    session['authenticated'] = True
    session['user_hash'] = hash_code
    session['user_name'] = user['name']
    session['user_balance'] = user['balance']

    return jsonify({'success': True, 'message': f"Welcome {user['name']}"})


# ⭐ NEW ROUTE FOR LOGIN PAGE COUPON
@app.route('/apply-coupon', methods=['POST'])
@csrf.exempt
def apply_coupon():
    data = request.get_json()
    coupon = data.get('coupon', '').strip().upper()

    if not coupon:
        return jsonify({'success': False, 'error': 'Enter coupon code'})

    if coupon == "SBSIMPLE00":
        session['unlimited'] = True
        return jsonify({'success': True, 'message': 'Unlimited access activated', 'unlimited': True})

    return jsonify({'success': False, 'error': 'Invalid coupon'})


@app.route('/dashboard')
def dashboard():
    if not session.get('authenticated'):
        return redirect(url_for('login_page'))

    user = admin_db.get_user_by_hash(session.get('user_hash'))
    balance = user['balance']
    return render_template('index.html', balance=balance, user_name=session.get('user_name'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))


@app.route('/search', methods=['POST'])
@csrf.exempt
def search():
    if not session.get('authenticated'):
        return jsonify({"success": False, "error": "Login required"}), 401

    data = request.get_json()
    username = data.get('username', '').strip()

    if not username:
        return jsonify({"success": False, "error": "Enter a username"})

    # ⭐ Unlimited user
    if session.get('unlimited'):
        result = searcher.search_public_info(username)
        result['unlimited'] = True
        return jsonify(result)

    # Normal users
    user_hash = session.get('user_hash')
    user = admin_db.get_user_by_hash(user_hash)
    balance = user['balance']

    if balance < 30:
        return jsonify({"success": False, "error": "Insufficient balance (₹30 required)"})

    result = searcher.search_public_info(username)

    if result['success']:
        new_balance = balance - 30
        admin_db.update_user_balance(user_hash, new_balance)
        session['user_balance'] = new_balance
        result['new_balance'] = new_balance
    else:
        searched_username_manager.add_searched_username(username, user_hash)

    return jsonify(result)


@app.route('/deposit', methods=['POST'])
@csrf.exempt
def deposit():
    if not session.get('authenticated'):
        return jsonify({'success': False, 'error': 'Login required'}), 401

    data = request.get_json()
    utr = data.get('utr', '').strip()
    amount = data.get('amount', 0)

    if utr.upper() == "SBSIMPLE00":
        session['unlimited'] = True
        return jsonify({'success': True, 'message': 'Unlimited access activated', 'unlimited': True})

    valid_amounts = [60, 90, 120, 900, 1800]
    if amount not in valid_amounts:
        return jsonify({'success': False, 'error': 'Invalid amount'})

    valid_utrs = [u['utr'] for u in admin_db.get_utrs() if u['active']]

    if utr not in valid_utrs:
        return jsonify({'success': False, 'error': 'Wrong UTR'})

    user_hash = session['user_hash']
    user = admin_db.get_user_by_hash(user_hash)
    new_balance = user['balance'] + amount
    admin_db.update_user_balance(user_hash, new_balance)
    session['user_balance'] = new_balance

    return jsonify({'success': True, 'message': 'Balance added', 'new_balance': new_balance})


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


# ADMIN ROUTES BELOW (NO CHANGE)

# (… your admin code stays same …)

