import os
import re
import time
import requests

from dotenv import load_dotenv


# ============================================================
# LOAD CONFIG
# ============================================================

load_dotenv()
TELEGRAM_API = (os.getenv("TELEGRAM_API_URL") or "@TELEGRAM_API").strip().rstrip("/")
YOUTUBE_API_URL = (os.getenv("YOUTUBE_API_URL") or "@YOUTUBE_API").strip().rstrip("/")

API_KEY = os.getenv("YOUTUBE_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TARGET_USERNAME = os.getenv(
    "TARGET_USERNAME",
    ""
).strip().lstrip("@").lower()

VIDEO_URL = os.getenv(
    "YOUTUBE_VIDEO_URL"
)


# ============================================================
# EXTRACT YOUTUBE VIDEO ID
# ============================================================

def extract_video_id(url):

    patterns = [
        r"(?:v=)([A-Za-z0-9_-]{11})",
        r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
        r"(?:youtube\.com/live/)([A-Za-z0-9_-]{11})",
    ]

    for pattern in patterns:

        match = re.search(pattern, url)

        if match:
            return match.group(1)

    return None


# ============================================================
# SEND TELEGRAM MESSAGE
# ============================================================

def send_telegram(message):

    url = (
        f"{TELEGRAM_API}/bot{TELEGRAM_TOKEN}/sendMessage"
    )

    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": True
    }

    response = requests.post(
        url,
        json=data,
        timeout=15
    )

    if response.status_code != 200:

        print("\n❌ Telegram error:")
        print(response.text)

        return False

    return True


# ============================================================
# CHECK WHETHER TARGET USERNAME IS IN MESSAGE
# ============================================================

def contains_target_username(text):

    if not text:
        return False

    text = text.lower()

    username = re.escape(
        TARGET_USERNAME
    )

    pattern = (
        rf"(?<![a-zA-Z0-9_])"
        rf"@?{username}"
        rf"(?![a-zA-Z0-9_])"
    )

    return re.search(
        pattern,
        text
    ) is not None


# ============================================================
# GET LIVE CHAT ID
# ============================================================

def get_live_chat_id(video_id):

    url = (
        f"{YOUTUBE_API_URL}/videos"
    )

    params = {
        "part": "snippet,liveStreamingDetails",
        "id": video_id,
        "key": API_KEY
    }

    response = requests.get(
        url,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    data = response.json()

    items = data.get(
        "items",
        []
    )

    if not items:

        raise RuntimeError(
            "YouTube video was not found."
        )

    video = items[0]

    snippet = video.get(
        "snippet",
        {}
    )

    live_details = video.get(
        "liveStreamingDetails",
        {}
    )

    title = snippet.get(
        "title",
        "Unknown"
    )

    channel = snippet.get(
        "channelTitle",
        "Unknown"
    )

    status = snippet.get(
        "liveBroadcastContent",
        "unknown"
    )

    chat_id = live_details.get(
        "activeLiveChatId"
    )

    return (
        chat_id,
        title,
        channel,
        status
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 60)
    print("        YOUTUBE LIVE CHAT MONITOR")
    print("=" * 60)
    print()

    # --------------------------------------------------------
    if not YOUTUBE_API_URL or YOUTUBE_API_URL.startswith("@"): 
        print("❌ YOUTUBE_API_URL missing")
        return

    # Validate config

    if not TELEGRAM_API or TELEGRAM_API.startswith("@" ):
        print("❌ TELEGRAM_API_URL missing" )
        return
    # --------------------------------------------------------

    if not API_KEY or API_KEY.startswith("@"):
        print("❌ YOUTUBE_API_KEY missing")
        return

    if not TELEGRAM_TOKEN or TELEGRAM_TOKEN.startswith("@"):
        print("❌ TELEGRAM_BOT_TOKEN missing")
        return

    if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID.startswith("@"):
        print("❌ TELEGRAM_CHAT_ID missing")
        return

    if not VIDEO_URL or VIDEO_URL.startswith("@"):
        print("❌ YOUTUBE_VIDEO_URL missing")
        return

    if not TARGET_USERNAME or TARGET_USERNAME.startswith('your_'):
        print('❌ TARGET_USERNAME is missing from .env')
        return

    print(
        f"Target: @{TARGET_USERNAME}"
    )

    # --------------------------------------------------------
    # Get video ID
    # --------------------------------------------------------

    video_id = extract_video_id(
        VIDEO_URL
    )

    if not video_id:

        print(
            "❌ Could not extract YouTube video ID."
        )

        return

    print(
        f"Video ID: {video_id}"
    )

    # --------------------------------------------------------
    # Get chat
    # --------------------------------------------------------

    print()
    print("Finding live chat...")

    try:

        (
            chat_id,
            title,
            channel,
            status
        ) = get_live_chat_id(
            video_id
        )

    except Exception as e:

        print(
            "❌ Could not get live chat:"
        )

        print(e)

        return

    print()
    print(f"Stream: {title}")
    print(f"Channel: {channel}")
    print(f"Status: {status}")

    if not chat_id:

        print()
        print(
            "❌ No active live chat found."
        )

        print(
            "Make sure the livestream is currently live."
        )

        return

    print()
    print("✅ Live chat connected.")

    # --------------------------------------------------------
    # Telegram connection test
    # --------------------------------------------------------

    print()
    print("Testing Telegram...")

    test_message = (
        "🟢 Giveaway Monitor connected!\n\n"
        f"Watching @{channel}\n"
        f"Looking for @{TARGET_USERNAME}"
    )

    if send_telegram(test_message):

        print(
            "✅ Telegram connection successful."
        )

    else:

        print(
            "❌ Telegram connection failed."
        )

        return

    # --------------------------------------------------------
    # START MONITORING
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("             MONITORING CHAT")
    print("=" * 60)
    print()
    print(
        f"Waiting for streamer to mention "
        f"@{TARGET_USERNAME}..."
    )
    print()
    print(
        "Press CTRL+C to stop."
    )
    print()

    page_token = None

    # Prevent duplicate alerts.
    alerted_message_ids = set()

    while True:

        try:

            params = {
                "part": "snippet,authorDetails",
                "liveChatId": chat_id,
                "maxResults": 200,
                "key": API_KEY
            }

            if page_token:

                params["pageToken"] = page_token

            response = requests.get(
                f"{YOUTUBE_API_URL}/liveChat/messages",
                params=params,
                timeout=20
            )

            # ------------------------------------------------
            # API error
            # ------------------------------------------------

            if response.status_code != 200:

                print()
                print(
                    "❌ YouTube Chat API error:"
                )

                print(
                    response.text
                )

                time.sleep(10)

                continue

            data = response.json()

            messages = data.get(
                "items",
                []
            )

            # ------------------------------------------------
            # Process messages
            # ------------------------------------------------

            for message in messages:

                message_id = message.get(
                    "id"
                )

                if not message_id:
                    continue

                if message_id in alerted_message_ids:
                    continue

                snippet = message.get(
                    "snippet",
                    {}
                )

                author = message.get(
                    "authorDetails",
                    {}
                )

                # We only care about normal
                # text chat messages.
                if snippet.get(
                    "type"
                ) != "textMessageEvent":

                    continue

                text = snippet.get(
                    "displayMessage",
                    ""
                )

                author_name = author.get(
                    "displayName",
                    "Unknown"
                )

                is_streamer = author.get(
                    "isChatOwner",
                    False
                )

                # ------------------------------------------------
                # Print streamer messages
                # ------------------------------------------------

                if is_streamer:

                    print(
                        f"🔴 [STREAMER] "
                        f"{author_name}: "
                        f"{text}"
                    )

                # ------------------------------------------------
                # Ignore everyone except streamer
                # ------------------------------------------------

                if not is_streamer:
                    continue

                # ------------------------------------------------
                # CHECK TARGET
                # ------------------------------------------------

                if contains_target_username(
                    text
                ):

                    print()
                    print("=" * 60)
                    print(
                        "🚨🚨🚨 TARGET DETECTED 🚨🚨🚨"
                    )
                    print("=" * 60)
                    print()
                    print(
                        f"Streamer: {author_name}"
                    )
                    print(
                        f"Message: {text}"
                    )
                    print()
                    print("=" * 60)

                    # Mark it so we don't alert twice.
                    alerted_message_ids.add(
                        message_id
                    )

                    # ------------------------------------------------
                    # TELEGRAM ALERT
                    # ------------------------------------------------

                    alert = (
                        "🚨🚨🚨 GIVEAWAY ALERT 🚨🚨🚨\n\n"
                        "YOUR USERNAME WAS MENTIONED!\n\n"
                        f"👤 Streamer: {author_name}\n\n"
                        f"💬 Message:\n{text}\n\n"
                        "⚠️ CHECK YOUTUBE NOW!\n"
                        "⚠️ YOU MAY HAVE WON!\n\n"
                        "⏱️ YOU HAVE 60 SECONDS!"
                    )

                    success = send_telegram(
                        alert
                    )

                    if success:

                        print()
                        print(
                            "📱 Telegram alert SENT!"
                        )

                    else:

                        print()
                        print(
                            "❌ Telegram alert FAILED!"
                        )

            # ------------------------------------------------
            # Get next page token
            # ------------------------------------------------

            page_token = data.get(
                "nextPageToken"
            )

            # ------------------------------------------------
            # Respect YouTube's polling interval
            # ------------------------------------------------

            polling_ms = data.get(
                "pollingIntervalMillis",
                5000
            )

            polling_seconds = max(
                polling_ms / 1000,
                5
            )

            time.sleep(
                polling_seconds
            )

        # ----------------------------------------------------
        # CTRL+C
        # ----------------------------------------------------

        except KeyboardInterrupt:

            print()
            print(
                "🛑 Giveaway monitor stopped."
            )

            break

        # ----------------------------------------------------
        # Network errors
        # ----------------------------------------------------

        except requests.RequestException as e:

            print()
            print(
                "⚠️ Network error:"
            )

            print(e)

            print(
                "Retrying in 10 seconds..."
            )

            time.sleep(10)

        # ----------------------------------------------------
        # Other errors
        # ----------------------------------------------------

        except Exception as e:

            print()
            print(
                "⚠️ Unexpected error:"
            )

            print(
                type(e).__name__,
                e
            )

            print(
                "Retrying in 10 seconds..."
            )

            time.sleep(10)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()