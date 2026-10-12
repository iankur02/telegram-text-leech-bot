import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_ID = int(os.environ.get("API_ID", "0"))
    API_HASH = os.environ.get("API_HASH", "").strip()
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()

    OWNER_ID = [
        int(x.strip()) for x in os.environ.get("OWNER_ID", "0").split(",") if x.strip().isdigit()
    ]
    if not OWNER_ID:
        OWNER_ID = [0]

    DUMP_CHANNEL = int(os.environ.get("DUMP_CHANNEL", "0"))
    PORT = int(os.environ.get("PORT", "8080"))
    WEB_SERVER = os.environ.get("WEB_SERVER", "true").lower() in ("true", "1", "yes")

    DOWNLOAD_DIR = os.environ.get("DOWNLOAD_DIR", "downloads")
    THUMB_DIR = os.environ.get("THUMB_DIR", "thumbnails")
    TG_MAX_FILE_SIZE = 2097152000

    USER_AGENT = os.environ.get(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    )
    PROGRESS_UPDATE_INTERVAL = int(os.environ.get("PROGRESS_UPDATE_INTERVAL", "4"))
