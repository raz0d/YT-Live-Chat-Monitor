import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_API_URL = (os.getenv("YOUTUBE_API_URL") or "@YOUTUBE_API").strip().rstrip("/")
VIDEO_URL = os.getenv("YOUTUBE_VIDEO_URL")


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


if not API_KEY or API_KEY.startswith("@"):
    print("❌ YOUTUBE_API_KEY is missing from .env")
    exit()

if not VIDEO_URL or VIDEO_URL.startswith("@"):
    print("❌ YOUTUBE_VIDEO_URL is missing from .env")
    exit()

if not YOUTUBE_API_URL or YOUTUBE_API_URL.startswith("@"):
    print("❌ YOUTUBE_API_URL is missing from .env")
    exit()


video_id = extract_video_id(VIDEO_URL)

if not video_id:
    print("❌ Could not extract the YouTube video ID.")
    print("Check your YOUTUBE_VIDEO_URL.")
    exit()


print("YouTube video ID:", video_id)
print()
print("Contacting YouTube API...")


url = f"{YOUTUBE_API_URL}/videos"

params = {
    "part": "snippet,liveStreamingDetails",
    "id": video_id,
    "key": API_KEY
}

response = requests.get(url, params=params)

print("HTTP status:", response.status_code)
print()


if response.status_code != 200:
    print("❌ YouTube API request failed.")
    print(response.text)
    exit()


data = response.json()

items = data.get("items", [])

if not items:
    print("❌ YouTube returned no video.")
    print("Check that the URL is correct and the video is accessible.")
    exit()


video = items[0]

snippet = video.get("snippet", {})
live_details = video.get("liveStreamingDetails", {})

title = snippet.get("title", "Unknown")
channel = snippet.get("channelTitle", "Unknown")
status = snippet.get("liveBroadcastContent", "unknown")

chat_id = live_details.get("activeLiveChatId")


print("========================================")
print("        YOUTUBE API TEST SUCCESS")
print("========================================")
print()
print("Title:")
print(title)
print()
print("Channel:")
print(channel)
print()
print("Broadcast status:")
print(status)
print()
print("Active live chat:")
print("YES" if chat_id else "NO")
print()


if chat_id:
    print("Live Chat ID found:")
    print(chat_id)
    print()
    print("🎉 We can now connect the giveaway monitor!")
else:
    print("No active live chat was found.")
    print()
    print("This is normal if the stream has not started yet.")