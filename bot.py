from flask import Flask, jsonify
import requests
import time
import random
import string
import os
import logging
import json
from dotenv import load_dotenv
from threading import Thread

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
OWNER_ID = os.getenv("OWNER_ID")

# Setup Flask
app = Flask(__name__)

# Setup logging
if not os.path.exists("logs"):
    os.makedirs("logs")

logging.basicConfig(
    filename="logs/bot.log",
    filemode="a",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(message)s")
console.setFormatter(formatter)
logging.getLogger().addHandler(console)

# Coupon generator
def generate_coupon():
    fixed = "K6GLNG7"
    random_part = ''.join(random.choices(string.ascii_uppercase, k=5))
    coupon = fixed + random_part
    logging.info(f"🎟️ Generated Coupon: {coupon}")
    return coupon

# Random device_id
def generate_device_id():
    fixed = "5428a65f-500a-4528-bfbe-"
    random_part = ''.join(random.choices('abcdef0123456789', k=6))
    device_id = fixed + random_part
    logging.info(f"🧾 Generated device_id: {device_id}")
    return device_id

# API call
def apply_coupon(coupon):
    url = "https://api2.ottplay.com/api/payment-service/v3.2/web/coupon/v1/apply?error_version=2"
    headers = {
        "Authorization": "Bearer F421D63D166CA343454DD833B599C",  # You should ideally auto-fetch this
        "content-type": "application/json;charset=UTF-8",
        "device_id": generate_device_id(),
        "devicetype": "web"
    }
    payload = {
        "product_id": "74189000045437359",
        "plan_code": "ott_bajaj_customquarterly",
        "coupon": coupon
    }

    logging.info(f"📡 Sending request with coupon: {coupon}")
    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        logging.info(f"📥 Full API Response:\n{json.dumps(data, indent=2)}")
        return data
    except Exception as e:
        logging.error(f"❌ Error in API call: {str(e)}")
        return {"error": str(e)}

# Telegram notify
def send_message(text):
    telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    try:
        response = requests.post(telegram_url, data=payload)
        if response.status_code == 200:
            logging.info("✅ Telegram message sent.")
        else:
            logging.error(f"❌ Telegram message failed: {response.text}")
    except Exception as e:
        logging.error(f"❌ Telegram send error: {str(e)}")

# Coupon worker
def coupon_worker():
    logging.info("🎯 Coupon worker started.")
    while True:
        coupon = generate_coupon()
        result = apply_coupon(coupon)

        code = result.get("code")
        message = result.get("message", "")
        coupon_code = result.get("couponCode", coupon)

        if code == 1022 and "successfully" in message.lower():
            text = f"✅ Coupon Applied!\nCode: {code}\nCoupon: {coupon_code}\nMessage: {message}"
            logging.info("🔔 Sending Telegram success notification...")
            send_message(text)
        else:
            logging.info("❌ Coupon not successful or ignored.")

        wait = random.uniform(1, 2)  # Random wait between 1–2 sec
        logging.info(f"⏳ Waiting {wait:.2f} seconds before next hit...")
        time.sleep(wait)

# Flask routes
@app.route("/")
def home():
    return "👋 OTT Coupon Bot is Live on Render!"

@app.route("/start")
def start():
    if CHAT_ID != OWNER_ID:
        logging.warning("❌ Unauthorized access to /start")
        return jsonify({"error": "Unauthorized"}), 403

    welcome_text = "🤖 Welcome to OTT Coupon Bot!\nOnly authorized user can use this bot."
    logging.info("👋 Sending welcome message.")
    send_message(welcome_text)
    return jsonify({"message": "Welcome message sent."})

# Start everything
if __name__ == "__main__":
    logging.info("🚀 Starting Flask server...")

    try:
        send_message("✅ Coupon bot started and running in background...")
        logging.info("📨 Telegram notified: Bot started.")
    except Exception as e:
        logging.error(f"❌ Failed to notify bot start: {str(e)}")

    # Background coupon loop
    t = Thread(target=coupon_worker)
    t.daemon = True
    t.start()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
