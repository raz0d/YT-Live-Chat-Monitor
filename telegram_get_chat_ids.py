"""Print Telegram chat IDs from recent bot messages, without printing the bot token."""

import os

import requests
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token or token.startswith("@") :
        raise SystemExit("TELEGRAM_BOT_TOKEN is missing from your local .env file.")

    telegram_api = (os.getenv("TELEGRAM_API_URL") or "@TELEGRAM_API").strip().rstrip("/")
    if telegram_api.startswith("@"):
        raise SystemExit("TELEGRAM_API_URL is missing from your local .env file.")

    response = requests.get(
        f"{telegram_api}/bot{token}/getUpdates",
        params={"limit": 100, "allowed_updates": '["message"]'},
        timeout=30,
    )
    data = response.json()
    if not response.ok or not data.get("ok"):
        raise SystemExit("Telegram getUpdates failed: " + data.get("description", "Unknown error"))

    chats = {}
    for update in data.get("result", []):
        message = update.get("message", {})
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        if chat_id is None:
            continue
        sender = message.get("from", {})
        name = " ".join(
            part for part in (sender.get("first_name", ""), sender.get("last_name", "")) if part
        ) or chat.get("title", "Unknown")
        chats[str(chat_id)] = name

    if not chats:
        print("No recent messages found. Ask each recipient to send /start and then a short message to the bot, then run this again.")
        return

    print("Recent Telegram chats (match the name, then copy that chat ID into your local .env):")
    for chat_id, name in chats.items():
        print(f"{name}: {chat_id}")
    print("Keep these IDs private; do not paste them into ChatGPT.")


if __name__ == "__main__":
    main()
