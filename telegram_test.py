import os

import requests
from dotenv import load_dotenv


load_dotenv()
TELEGRAM_API = (os.getenv("TELEGRAM_API_URL") or "@TELEGRAM_API").strip().rstrip("/")

TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
CHAT_IDS = [
    chat_id.strip()
    for chat_id in (os.getenv("TELEGRAM_CHAT_IDS") or "").split(",")
    if chat_id.strip()
]
if not CHAT_IDS or any(chat_id.startswith("@") for chat_id in CHAT_IDS):
    old_chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
    if old_chat_id:
        CHAT_IDS = [old_chat_id]

if not TOKEN or TOKEN.startswith("@"):
    raise SystemExit("ERROR: TELEGRAM_BOT_TOKEN is missing from .env")

if not CHAT_IDS or any(chat_id.startswith("@") for chat_id in CHAT_IDS):
    raise SystemExit("ERROR: Add TELEGRAM_CHAT_IDS (or TELEGRAM_CHAT_ID) to .env")

if not TELEGRAM_API or TELEGRAM_API.startswith("@"):
    raise SystemExit("ERROR: TELEGRAM_API_URL is missing from .env" )

url = f"{TELEGRAM_API}/bot{TOKEN}/sendMessage"
message = "🟢 TEST SUCCESS!\n\nYour Giveaway Bot can send Telegram messages."

for index, chat_id in enumerate(CHAT_IDS, start=1):
    try:
        response = requests.post(
            url,
            json={
                "chat_id": chat_id,
                "text": message,
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        result = response.json()
    except requests.RequestException:
        print(f"Recipient {index}: FAILED (network request error; sensitive URL omitted)")
        continue
    except ValueError:
        print(f"Recipient {index}: FAILED (Telegram returned a non-JSON response)")
        continue

    if response.ok and result.get("ok"):
        print(f"Recipient {index}: test message sent successfully.")
    else:
        description = result.get("description", "Telegram returned an error.")
        print(f"Recipient {index}: FAILED ({description})")
