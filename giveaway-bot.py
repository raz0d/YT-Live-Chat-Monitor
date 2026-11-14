import os
import requests
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_API = (os.getenv("TELEGRAM_API_URL") or "@TELEGRAM_API").strip().rstrip("/")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TOKEN or TOKEN.startswith("@"):
    print("ERROR: TELEGRAM_BOT_TOKEN is missing from .env")
    exit()

if not CHAT_ID or CHAT_ID.startswith("@"):
    print("ERROR: TELEGRAM_CHAT_ID is missing from .env")
    exit()

if not TELEGRAM_API or TELEGRAM_API.startswith("@"):
    print("ERROR: TELEGRAM_API_URL is missing from .env" )
    exit()

url = f"{TELEGRAM_API}/bot{TOKEN}/sendMessage"

data = {
    "chat_id": CHAT_ID,
    "text": "🟢 TEST SUCCESS!\n\nYour Giveaway Bot can send Telegram messages."
}

response = requests.post(url, json=data)

print("HTTP status:", response.status_code)
print("Telegram response:")
print(response.text)