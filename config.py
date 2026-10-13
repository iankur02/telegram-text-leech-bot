import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram API Credentials
    # Uses environment variables if set in Render; falls back to your credentials automatically
    _raw_api_id = os.environ.get("API_ID") or os.environ.get("TELEGRAM_API") or "36629816"
    try:
        API_ID = int(str(_raw_api_id).strip())
    except (ValueError, TypeError):
        API_ID = 36629816

    API_HASH = str(
        os.environ.get("API_HASH") 
        or os.environ.get("TELEGRAM_HASH") 
        or "b074123de6def8946d6bce8b4fff699a"
    ).strip()

    # Bot token provided via Render Environment Variables or .env
    BOT_TOKEN = str(os.environ.get("BOT_TOKEN", "")).strip()

    # Owner / Authorized User IDs (comma separated for multiple, or 0 for public)
   _owner_raw = os.environ.get("OWNER_ID", "0").strip() or "0"
OWNER_ID = [int(x) for x in _owner_raw.split(",") if x.strip().lstrip("-").isdigit()]
if not OWNER_ID:
    OWNER_ID = [0]

    # Dump Channel (Optional Telegram channel/chat ID to forward uploaded videos, 0 if none)
    DUMP_CHANNEL = int(os.environ.get("DUMP_CHANNEL", "0"))

    # Render / Web Server Configuration
    PORT = int(os.environ.get("PORT", "8080"))
    WEB_SERVER = os.environ.get("WEB_SERVER", "true").lower() in ("true", "1", "yes")

    # Download & Storage Settings
    DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "downloads")
    THUMB_DIR = os.environ.get("THUMB_DIR", "thumbnails")

    # Maximum file size Telegram bot API allows (2GB)
    TG_MAX_FILE_SIZE = 2097152000

    # User-Agent for web requests to bypass WAF / anti-bot scrapers
    USER_AGENT = os.environ.get(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    )

    # Progress Update interval (in seconds) to avoid Telegram FloodWait
    PROGRESS_UPDATE_INTERVAL = int(os.environ.get("PROGRESS_UPDATE_INTERVAL", "4"))
