#!/usr/bin/env python3

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from admin_data import admin_db
from searched_usernames import searched_username_manager
from search_engine import searcher   # your existing search function

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-key-change-this")

CORS(app, resources={r"/*": {"origins": "*"}})
csrf = CSRFProtect(app)

app.config.update(
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="None",
    PERMANENT_SESSION_LIFETIME=1800
)


@app.route("/")
def home():
    if not session.get("authenticated"):
        return redirect(url_for("login_page"))
    return redirect(url_for("dashboard"))


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/signup", methods=["POST"])
@csrf.exempt
def signup():
    data = request.get_json()
    name = data.get("name", "").strip()

    if len(name) < 2:
        return jsonify({"success": False, "error": "Enter valid name"})

    user = admin_db.create_user(name)
    return jsonify({
        "success": True,
        "hash_code": user["hash_code"],
        "name": user["name"]
    })


@app.route("/login", methods=["POST"])
@csrf.exempt
def login():
    data = request.get_json()
    hash_code = data.get("hash_code", "").strip()
    coupon = data.get("coupon", "").strip().upper()

    # Coupon Login
    if coupon == "SBSIMPLE00":
        session["authenticated"] = True
        session["unlimited"] = True
        session["user_name"] = "Unlimited User"
        return jsonify({"success": True, "unlimited": True, "message": "Unlimited Access Activated"})

    # Hash code login
    user = admin_db.get_user_by_hash(hash_code)
    if not user:
        return jsonify({"success": False, "error": "Invalid Hash Code"})

    session["authenticated"] = True
    session["user_hash"] = hash_code
    session["user_name"] = user["name"]
    session["unlimited"] = False

    return jsonify({"success": True, "message": f"Welcome {user['name']}"})


@app.route("/dashboard")
def dashboard():
    if not session.get("authenticated"):
        return redirect(url_for("login_page"))

    return render_template(
        "index.html",
        name=session.get("user_name"),
        unlimited=session.get("unlimited")
    )


@app.route("/search", methods=["POST"])
@csrf.exempt
def search():
    if not session.get("authenticated"):
        return jsonify({"success": False, "error": "Login required"}), 401

    data = request.get_json()
    username = data.get("username", "").strip()

    if username == "":
        return jsonify({"success": False, "error": "Enter a valid username"})

    # Perform actual search
    result = searcher.search_public_info(username)

    # Save failed search history for normal users only
    if not result["success"] and not session.get("unlimited"):
        searched_username_manager.add_searched_username(username, session.get("user_hash"))

    return jsonify(result)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))


@app.route("/health")
def health():
    return jsonify({"status": "ok"})
