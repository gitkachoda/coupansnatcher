import os
import time
import random
import string
import threading
import requests
from dotenv import load_dotenv
from datetime import datetime
from flask import Flask, jsonify

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
BASE_COUPON = os.getenv("BASE_COUPON")
COOKIES = os.getenv("FLIPKART_COOKIES")

LOG_FILE = "coupon_log.txt"
RUNNING = True

app = Flask(__name__)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Telegram Error:", e)

def generate_random_code():
    return BASE_COUPON + ''.join(random.choices(string.ascii_uppercase + string.digits, k=13))

def try_coupon(coupon_code):
    url = "https://1.rome.api.flipkart.com/api/1/action/view"
    headers = {
        "content-type": "application/json",
        "cookie": COOKIES,
        "flipkart_secure": "true",
        "host": "1.rome.api.flipkart.com",
        "origin": "https://www.flipkart.com",
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36",
        "referer": "https://www.flipkart.com/",
        "x-user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Mobile Safari/537.36 FKUA/msite/0.0.3/msite/Mobile"
    }
    payload = {
        "actionRequestContext": {
            "type": "CLAIM_COUPON",
            "couponCode": coupon_code
        }
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=20)
        data = response.json()
        action_success = data.get("RESPONSE", {}).get("actionSuccess", None)
        error_message = data.get("RESPONSE", {}).get("errorMessage", "")
        
        log_entry = f"[{datetime.now()}] CODE: {coupon_code} | SUCCESS: {action_success} | ERROR: {error_message}"
        
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")

        # Only send message when max redemption limit is reached
        if "You have reached maximum redemption limit" in error_message:
            telegram_text = (
                f"🟩 <b>Coupon Tried:</b> {coupon_code}\n"
                f"✅ <b>Success:</b> {action_success}\n"
                f"<b>Message:</b> {error_message}"
            )
            send_telegram_message(telegram_text)

        print(log_entry)

    except Exception as e:
        print("Request Error:", e)

def coupon_worker():
    while RUNNING:
        code = generate_random_code()
        try_coupon(code)
        # Optional delay
        # time.sleep(random.randint(1, 3))

@app.route("/")
def home():
    return jsonify({"status": "running", "message": "Coupon bot active"})

@app.route("/logs")
def get_logs():
    if not os.path.exists(LOG_FILE):
        return jsonify({"logs": []})
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        logs = f.readlines()
    return jsonify({"logs": logs[-50:]})

@app.route("/status")
def status():
    return jsonify({"running": RUNNING})

# Run background thread when server starts
@app.before_first_request
def start_worker():
    send_telegram_message("✅ <b>Coupon Bot Started</b>\nServer is now running and trying coupons...")
    t = threading.Thread(target=coupon_worker, daemon=True)
    t.start()
