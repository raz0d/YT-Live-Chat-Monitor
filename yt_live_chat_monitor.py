"""Monitor a configured YouTube livestream and alert on target mentions."""

import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
from dotenv import load_dotenv


load_dotenv()

YOUTUBE_API = (os.getenv("YOUTUBE_API_URL") or "@YOUTUBE_API").strip().rstrip("/")
TELEGRAM_API = (os.getenv("TELEGRAM_API_URL") or "@TELEGRAM_API").strip().rstrip("/")
CHANNEL_HANDLE = os.getenv("YOUTUBE_CHANNEL_HANDLE", "").strip()
VIDEO_URL_TEMPLATE = (os.getenv("YOUTUBE_VIDEO_URL_TEMPLATE") or "@VIDEO_URL").strip()
DISCOVERY_INTERVAL = max(60, int(os.getenv("DISCOVERY_INTERVAL_SECONDS", "1200")))
REQUEST_TIMEOUT = 20
OWNER_ALERT_REPEAT_COUNT = 15
OWNER_ALERT_INTERVAL_SECONDS = 1.05


class YouTubeAPIError(RuntimeError):
    def __init__(self, status: int, reason: str, message: str):
        super().__init__(message)
        self.status = status
        self.reason = reason


def parse_csv(value: Optional[str]) -> List[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def get_config() -> Tuple[str, str, List[str], List[str]]:
    api_key = (os.getenv("YOUTUBE_API_KEY") or "").strip()
    telegram_token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    targets = [name.lstrip("@").casefold() for name in parse_csv(os.getenv("TARGET_USERNAMES"))]

    chat_ids = parse_csv(os.getenv("TELEGRAM_CHAT_IDS"))
    if not chat_ids:
        legacy_chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()
        if legacy_chat_id:
            chat_ids = [legacy_chat_id]

    missing = []
    if not api_key or api_key.startswith("@"):
        missing.append("YOUTUBE_API_KEY")
    if not YOUTUBE_API or YOUTUBE_API.startswith("@"):
        missing.append("YOUTUBE_API_URL")
    if not telegram_token or telegram_token.startswith("@"):
        missing.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_API or TELEGRAM_API.startswith("@"):
        missing.append("TELEGRAM_API_URL")
    if not VIDEO_URL_TEMPLATE or VIDEO_URL_TEMPLATE.startswith("@") or "{video_id}" not in VIDEO_URL_TEMPLATE:
        missing.append("YOUTUBE_VIDEO_URL_TEMPLATE (must contain {video_id})")
    if not CHANNEL_HANDLE or CHANNEL_HANDLE.upper() == "@CHANNEL_HANDLE":
        missing.append("YOUTUBE_CHANNEL_HANDLE")
    if not targets or any(name.startswith(("target_", "second_target_", "your_")) for name in targets):
        missing.append("TARGET_USERNAMES")
    if not chat_ids or any(chat_id.startswith("@") for chat_id in chat_ids):
        missing.append("TELEGRAM_CHAT_IDS (or legacy TELEGRAM_CHAT_ID)")
    if missing:
        raise ValueError("Missing required .env setting(s): " + ", ".join(missing))
    return api_key, telegram_token, targets, chat_ids
def youtube_get(path: str, api_key: str, params: Dict[str, Any]) -> Dict[str, Any]:
    query = dict(params)
    query["key"] = api_key
    response = requests.get(f"{YOUTUBE_API}/{path}", params=query, timeout=REQUEST_TIMEOUT)
    try:
        body = response.json()
    except ValueError:
        body = {}
    if not response.ok:
        errors = body.get("error", {}).get("errors", [])
        reason = errors[0].get("reason", "unknown") if errors else "unknown"
        message = body.get("error", {}).get("message", response.text[:300])
        raise YouTubeAPIError(response.status_code, reason, message)
    return body


def resolve_channel_id(api_key: str) -> str:
    data = youtube_get(
        "channels",
        api_key,
        {"part": "id", "forHandle": CHANNEL_HANDLE.lstrip("@")},
    )
    items = data.get("items", [])
    if not items:
        raise RuntimeError(f"YouTube did not find channel {CHANNEL_HANDLE}.")
    channel_id = items[0].get("id")
    if not channel_id:
        raise RuntimeError("YouTube returned a channel without an ID.")
    return channel_id


def find_live_stream(api_key: str, channel_id: str) -> Optional[Dict[str, str]]:
    data = youtube_get(
        "search",
        api_key,
        {
            "part": "snippet",
            "channelId": channel_id,
            "type": "video",
            "eventType": "live",
            "order": "date",
            "maxResults": 5,
        },
    )
    for item in data.get("items", []):
        video_id = item.get("id", {}).get("videoId")
        snippet = item.get("snippet", {})
        if video_id:
            return {
                "video_id": video_id,
                "title": snippet.get("title", "(untitled stream)"),
                "channel_title": snippet.get("channelTitle", CHANNEL_HANDLE),
            }
    return None


def get_active_chat_id(api_key: str, video_id: str) -> Tuple[Optional[str], Optional[str]]:
    data = youtube_get(
        "videos",
        api_key,
        {"part": "snippet,liveStreamingDetails", "id": video_id},
    )
    items = data.get("items", [])
    if not items:
        return None, None
    details = items[0].get("liveStreamingDetails", {})
    status = items[0].get("snippet", {}).get("liveBroadcastContent")
    return details.get("activeLiveChatId"), status


def matches_targets(message: str, targets: List[str]) -> List[str]:
    found = []
    for username in targets:
        pattern = rf"(?<![A-Za-z0-9_])@?{re.escape(username)}(?![A-Za-z0-9_])"
        if re.search(pattern, message, flags=re.IGNORECASE):
            found.append(username)
    return found


def send_telegram(token: str, chat_ids: List[str], text: str) -> int:
    sent = 0
    for chat_id in chat_ids:
        response = requests.post(
            f"{TELEGRAM_API}/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            timeout=REQUEST_TIMEOUT,
        )
        try:
            body = response.json()
        except ValueError:
            body = {}
        if response.ok and body.get("ok"):
            sent += 1
            logging.info("Telegram alert delivered to a configured recipient.")
        else:
            description = body.get("description", response.text[:300])
            logging.error("Telegram delivery failed for one recipient: %s", description)
    return sent


def is_chat_ended(error: YouTubeAPIError) -> bool:
    return error.reason in {"liveChatEnded", "liveChatNotFound"} or error.status == 404


def monitor_stream(
    api_key: str,
    telegram_token: str,
    chat_ids: List[str],
    targets: List[str],
    channel_id: str,
    stream: Dict[str, str],
) -> None:
    video_id = stream["video_id"]
    video_url = VIDEO_URL_TEMPLATE.format(video_id=video_id)
    logging.info("Live stream found: %s (%s)", stream["title"], video_url)

    chat_id = None
    while chat_id is None:
        try:
            chat_id, broadcast_status = get_active_chat_id(api_key, video_id)
            if chat_id is None:
                if broadcast_status != "live":
                    logging.info("The broadcast ended or its live chat is unavailable. Returning to discovery.")
                    return
                logging.info("Waiting for this stream's live chat to become available...")
                time.sleep(30)
        except YouTubeAPIError as exc:
            if exc.reason in {"quotaExceeded", "dailyLimitExceeded"}:
                raise
            logging.warning("Could not get the live chat yet (%s). Retrying in 30 seconds.", exc.reason)
            time.sleep(30)

    logging.info("Connected to live chat. Watching for: %s", ", ".join("@" + t for t in targets))
    page_token = None
    handled_message_ids: Set[str] = set()

    while True:
        params: Dict[str, Any] = {
            "part": "snippet,authorDetails",
            "liveChatId": chat_id,
            "maxResults": 200,
        }
        if page_token:
            params["pageToken"] = page_token

        try:
            data = youtube_get("liveChat/messages", api_key, params)
        except YouTubeAPIError as exc:
            if is_chat_ended(exc):
                logging.info("The live chat ended. Returning to stream discovery.")
                return
            if exc.reason in {"quotaExceeded", "dailyLimitExceeded"}:
                logging.error("YouTube API quota reached; pausing for 15 minutes: %s", exc)
                time.sleep(900)
                continue
            logging.warning("YouTube chat request failed (%s); retrying in 10 seconds.", exc.reason)
            time.sleep(10)
            continue
        except requests.RequestException as exc:
            logging.warning("Network error reading chat: %s; retrying in 10 seconds.", exc)
            time.sleep(10)
            continue

        for message in data.get("items", []):
            message_id = message.get("id")
            if not message_id or message_id in handled_message_ids:
                continue
            snippet = message.get("snippet", {})
            if snippet.get("type") != "textMessageEvent":
                continue

            author = message.get("authorDetails", {})
            author_name = author.get("displayName", "Unknown viewer")
            author_channel_id = author.get("channelId") or snippet.get("authorChannelId")
            is_owner = author_channel_id == channel_id or author.get("isChatOwner", False)
            text = snippet.get("displayMessage", "")
            logging.info("[CHAT] %s: %s", author_name, text)

            matches = matches_targets(text, targets)
            if not matches:
                continue
            handled_message_ids.add(message_id)
            repeat_count = OWNER_ALERT_REPEAT_COUNT if is_owner else 1
            sender_type = "stream owner" if is_owner else "viewer"
            logging.warning("Target mention detected from %s (%s): %s", author_name, sender_type, text)

            for alert_number in range(1, repeat_count + 1):
                alert = (
                    "🚨 YOUTUBE LIVE CHAT ALERT 🚨\n\n"
                    f"Mentioned: {', '.join('@' + name for name in matches)}\n"
                    f"Chat sender: {author_name}\n"
                    f"Message: {text}\n\n"
                    f"Open the livestream now: {video_url}"
                )
                if is_owner:
                    alert += f"\n\nAlert {alert_number} of {repeat_count}"

                delivered = send_telegram(telegram_token, chat_ids, alert)
                if delivered < len(chat_ids):
                    logging.error(
                        "Alert %d delivered to %d of %d configured recipients.",
                        alert_number,
                        delivered,
                        len(chat_ids),
                    )
                if alert_number < repeat_count:
                    # Keep each private chat at or below Telegram's recommended rate.
                    time.sleep(OWNER_ALERT_INTERVAL_SECONDS)

        page_token = data.get("nextPageToken")
        wait_ms = data.get("pollingIntervalMillis", 5000)
        time.sleep(max(1, wait_ms / 1000))


def run() -> None:
    load_dotenv()
    api_key, telegram_token, targets, chat_ids = get_config()
    logging.info("Targets: %s", ", ".join("@" + name for name in targets))
    logging.info("Configured Telegram recipients: %d", len(chat_ids))
    if len(chat_ids) < 2:
        logging.warning("Only one recipient is configured. Add each recipient to TELEGRAM_CHAT_IDS after they start the bot.")

    while True:
        try:
            channel_id = resolve_channel_id(api_key)
            break
        except YouTubeAPIError as exc:
            delay = 1800 if exc.reason in {"quotaExceeded", "dailyLimitExceeded"} else 60
            logging.error("Could not resolve the YouTube channel (%s): %s; retrying in %d seconds.", exc.reason, exc, delay)
            time.sleep(delay)
        except requests.RequestException as exc:
            logging.error("Network error resolving the channel: %s; retrying in 60 seconds.", exc)
            time.sleep(60)
    logging.info("Resolved %s to channel ID %s", CHANNEL_HANDLE, channel_id)
    logging.info("Searching for a live stream every %d minutes while idle.", DISCOVERY_INTERVAL // 60)

    while True:
        try:
            stream = find_live_stream(api_key, channel_id)
            if stream:
                monitor_stream(api_key, telegram_token, chat_ids, targets, channel_id, stream)
                # Avoid rediscovering the same broadcast immediately after chat ends.
                time.sleep(60)
            else:
                logging.info("No live stream found. Checking again in %d minutes.", DISCOVERY_INTERVAL // 60)
                time.sleep(DISCOVERY_INTERVAL)
        except KeyboardInterrupt:
            logging.info("Bot stopped.")
            return
        except YouTubeAPIError as exc:
            if exc.reason in {"quotaExceeded", "dailyLimitExceeded"}:
                logging.error("YouTube quota reached; retrying discovery in 30 minutes: %s", exc)
                time.sleep(1800)
            else:
                logging.error("YouTube API error (%s): %s; retrying in 60 seconds.", exc.reason, exc)
                time.sleep(60)
        except requests.RequestException as exc:
            logging.error("Network error: %s; retrying in 60 seconds.", exc)
            time.sleep(60)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    try:
        run()
    except ValueError as exc:
        logging.error("Configuration problem: %s", exc)
