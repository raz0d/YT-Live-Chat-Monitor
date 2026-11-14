# yt-live-chat-monitor

Monitor a public YouTube livestream chat for selected usernames and receive matching alerts in Telegram—so you can follow giveaway mentions and results without watching the stream continuously.

> The bot reads public live chat and sends private Telegram alerts. It does not post in YouTube chat or claim a giveaway.

## What it does

- Finds the configured channel’s active public livestream automatically.
- Watches live chat for one or more configured usernames, with or without `@`.
- Sends one alert per recipient when a viewer mentions a target.
- Sends 15 alerts per recipient when the stream owner mentions a target, spaced about one second apart.
- Retries temporary API/network errors and searches again when a stream ends.

## 1. Create a Telegram bot

1. Open [BotFather](https://t.me/BotFather) in Telegram and press **Start**.
2. Send `/newbot`.
3. Choose a display name, then a unique username ending in `bot` (for example, `ExampleAlertsBot`).
4. BotFather will return a bot token. Store it privately; anyone with the token can control the bot.

See Telegram’s [official bot creation guide](https://core.telegram.org/bots/features#botfather) for more detail.

## 2. Get the Telegram chat ID for alerts

The bot can only send a private message to a person after that person has opened the bot and sent it a message.

1. Open your new bot and send `/start`. Each alert recipient must do this once.
2. Set `TELEGRAM_API_URL` and `TELEGRAM_BOT_TOKEN` in your local `.env` file (see [Configure the project](#4-configure-the-project)).
3. Run the helper from the project folder:

   ```bash
   python telegram_get_chat_ids.py
   ```

4. The helper lists recent chat names and IDs. Copy the IDs for the people who should receive alerts into `TELEGRAM_CHAT_IDS`, separated by commas.

Keep chat IDs private. The helper reads recent bot updates and prints the matching names and IDs; it does not send messages.

## 3. Create a YouTube Data API key

The monitor uses the YouTube Data API to find the channel’s current livestream and read public live-chat messages.

1. Open the [Google Cloud Console](https://console.cloud.google.com/) and create or select a project.
2. In **APIs & Services → Library**, enable **YouTube Data API v3**.
3. In **APIs & Services → Credentials**, choose **Create credentials → API key**.
4. Restrict the key to the YouTube Data API v3 where possible, and keep it private.

This bot reads public YouTube data, so an API key is sufficient; OAuth is not required. See Google’s [YouTube Data API setup guide](https://developers.google.com/youtube/v3/getting-started) and [authorization guide](https://developers.google.com/youtube/data/guides/authentication). The API has quota limits, so avoid setting an unnecessarily short discovery interval; see [YouTube API quota costs](https://developers.google.com/youtube/v3/determine_quota_cost).

## 4. Configure the project

Copy the example file to `.env`:

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
```

**Linux or macOS**

```bash
cp .env.example .env
```

Replace every `@...` placeholder in `.env` with your own value:

| Setting | Value to enter |
| --- | --- |
| `YOUTUBE_API_URL` | `https://www.googleapis.com/youtube/v3` |
| `TELEGRAM_API_URL` | `https://api.telegram.org` |
| `YOUTUBE_API_KEY` | The API key from Google Cloud |
| `TELEGRAM_BOT_TOKEN` | The token from BotFather |
| `TELEGRAM_CHAT_IDS` | One or more recipient chat IDs, comma-separated |
| `YOUTUBE_CHANNEL_HANDLE` | The channel handle to monitor, such as `@ExampleChannel` |
| `YOUTUBE_VIDEO_URL_TEMPLATE` | A URL pattern containing `{video_id}`, for example `https://www.youtube.com/watch?v={video_id}` |
| `TARGET_USERNAMES` | The usernames that should trigger alerts, comma-separated |
| `DISCOVERY_INTERVAL_SECONDS` | How often to look for a livestream when none is active; default is `1200` seconds (20 minutes) |

**The target usernames go in `TARGET_USERNAMES`.** Any chat participant mentioning one of those names triggers an alert. Matching is case-insensitive and accepts an optional `@`.

The main monitor uses the channel handle to discover streams, so it does not need a fixed video URL. `YOUTUBE_VIDEO_URL_TEMPLATE` is used to create a clickable link in alerts.

The following are compatibility settings for older/manual diagnostic scripts; they are not needed by the main monitor:

- `YOUTUBE_VIDEO_URL`: one specific livestream URL.
- `TARGET_USERNAME`: one target username.
- `TELEGRAM_CHAT_ID`: one recipient ID. The main monitor supports this as a fallback when `TELEGRAM_CHAT_IDS` is empty.

The project’s `.gitignore` excludes `.env`, virtual environments, Python bytecode, editor settings, and private key files. Commit `.env.example`, never `.env` or an AWS `.pem` key.

## 5. Install and run locally

You need Python 3.9 or later.

**Windows PowerShell**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python telegram_test.py
python yt_live_chat_monitor.py
```

**Linux or macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python telegram_test.py
python yt_live_chat_monitor.py
```

`telegram_test.py` sends a test message to every configured recipient. The main monitor runs continuously; press `Ctrl+C` to stop it when running in a terminal.

The optional `youtube_test.py` and the older manual monitor scripts need the compatibility setting `YOUTUBE_VIDEO_URL`. The main monitor does not.

## 6. Create an affordable AWS Lightsail instance

Lightsail is a simple way to keep the bot running while your computer is off. AWS currently lists a Linux/Unix Nano plan with 0.5 GB RAM from **US$5/month**; check the [current Lightsail pricing](https://aws.amazon.com/lightsail/pricing/) and the price shown for your region before creating an instance.

1. Sign in to the [AWS Lightsail console](https://lightsail.aws.amazon.com/).
2. Choose **Create instance**.
3. Choose a region close to you or the YouTube/Telegram services you use.
4. Select **Linux/Unix → OS Only → Ubuntu** (an available Ubuntu LTS release).
5. Choose the smallest Linux/Unix bundle suitable for this lightweight monitor, then give the instance a name such as `yt-live-chat-monitor`.
6. Create the instance and wait until it is running. AWS’s [instance creation guide](https://docs.aws.amazon.com/lightsail/latest/userguide/how-to-create-amazon-lightsail-instance-virtual-private-server-vps.html) has screenshots and current console steps.

### Restrict network access

The bot makes outbound HTTPS requests and does not host a website. It does not need inbound HTTP or HTTPS ports. In the Lightsail firewall, keep SSH (TCP port 22) available only from your IP address when possible. AWS explains this in its [Lightsail firewall guide](https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-firewall-and-port-mappings-in-amazon-lightsail.html).

A static IP is optional. It keeps the instance address stable after a restart; AWS currently does not charge for a static IP while it is attached to an instance. See [create and attach a static IP](https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-create-static-ip.html).

## 7. Connect and install the bot on Ubuntu

In Lightsail, select your instance and choose **Connect using SSH**. This opens a browser-based terminal. You can also connect from your own SSH client; for Windows, the Lightsail SSH page shows how to use the regional `.pem` key. Keep that key outside the repository. See AWS’s [SSH connection guide](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-ssh-using-terminal.html).

Once connected, install Git and Python, then clone your GitHub repository. Replace `YOUR_GITHUB_USERNAME` if you use the example command:

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip
cd ~
git clone https://github.com/YOUR_GITHUB_USERNAME/yt-live-chat-monitor.git
cd yt-live-chat-monitor
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
nano .env
chmod 600 .env
```

Enter the real API URLs, keys, token, recipient IDs, channel handle, target usernames, and video URL template in the server’s `.env`. Do not commit or paste that file into GitHub. The `chmod 600` command limits access to the Ubuntu account.

Send a test message before starting the monitor:

```bash
.venv/bin/python telegram_test.py
```

Then run the monitor once in the terminal to confirm it starts and can find the channel:

```bash
.venv/bin/python yt_live_chat_monitor.py
```

Press `Ctrl+C` to stop the foreground run before creating the service below.

## 8. Keep it running with systemd

Create a service file:

```bash
sudo nano /etc/systemd/system/yt-live-chat-monitor.service
```

Paste the following:

```ini
[Unit]
Description=YouTube Live Chat Telegram Alert Bot
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/yt-live-chat-monitor
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/ubuntu/yt-live-chat-monitor/.venv/bin/python /home/ubuntu/yt-live-chat-monitor/yt_live_chat_monitor.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Save the file, then enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now yt-live-chat-monitor
sudo systemctl status yt-live-chat-monitor --no-pager
```

Useful service commands:

```bash
sudo journalctl -u yt-live-chat-monitor -f       # follow logs
sudo systemctl restart yt-live-chat-monitor       # restart after a code/config change
sudo systemctl stop yt-live-chat-monitor          # stop the bot
sudo systemctl start yt-live-chat-monitor         # start it again
```

The service starts after a reboot and restarts after an unexpected process failure. The Lightsail instance itself must remain running; AWS charges for the instance while it is provisioned. To stop using it, review the current billing and instance options in Lightsail.

## Troubleshooting

- **Missing settings:** Replace every `@...` value in `.env`. The main script exits with the names of any missing settings.
- **Telegram test fails:** Confirm the token and API URL, and make sure each recipient has sent `/start` to the bot. Check that every ID is in `TELEGRAM_CHAT_IDS`.
- **No livestream found:** Confirm `YOUTUBE_CHANNEL_HANDLE` is correct and that the channel has a public live stream. Discovery runs at the configured interval while idle.
- **YouTube quota errors:** Check quota in Google Cloud and allow the monitor to retry. YouTube API request costs vary by method.
- **Service logs:** Use `sudo journalctl -u yt-live-chat-monitor -f` on the Lightsail instance.

## Project files

- `yt_live_chat_monitor.py` — automatic livestream discovery, chat monitoring, and Telegram alerts.
- `telegram_get_chat_ids.py` — lists recent Telegram chat IDs for bot users who have messaged it.
- `telegram_test.py` — sends a test alert to configured recipients.
- `youtube_test.py`, `chat_test.py`, `giveaway_monitor.py`, and `giveaway-bot.py` — older/manual diagnostic helpers.
- `.env.example` — safe configuration template.
- `.gitignore` — excludes local secrets and generated files.

This project is released under the MIT License. The MIT License allows free use, modification, and redistribution as long as the copyright and license notice are retained.
