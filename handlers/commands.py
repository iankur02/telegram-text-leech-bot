import os
import shutil
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from core.media import MediaHelper

logger = logging.getLogger(__name__)

USER_THUMBNAILS = {}
ACTIVE_TASKS = {}
PENDING_CONFIG = {}

def is_authorized(user_id: int) -> bool:
    return (0 in Config.OWNER_ID) or (user_id in Config.OWNER_ID)

async def start_command(client: Client, message: Message):
    if not is_authorized(message.from_user.id):
        await message.reply_text("⛔ **Access Denied.**")
        return

    text = (
        f"👋 **Hello {message.from_user.first_name}!**\n\n"
        f"I am your **Text-to-Video Telegram Leech Bot**, optimized for Render.\n\n"
        f"📁 **How to use:**\n"
        f"1. Send me any `.txt` file containing video titles and URLs.\n"
        f"2. Headers and empty lines are automatically skipped.\n"
        f"3. Send a photo anytime to set a custom video thumbnail.\n\n"
        f"⚙️ **Commands:**\n"
        f"• `/thumb` - View/delete current thumbnail\n"
        f"• `/cancel` or `/stop` - Stop current batch\n"
        f"• `/stats` - View disk & memory status"
    )
    await message.reply_text(text)

async def help_command(client: Client, message: Message):
    if not is_authorized(message.from_user.id):
        return
    await message.reply_text(
        "📖 **Help & Supported Formats:**\n\n"
        "• Direct MP4, MKV, WebM links\n"
        "• HLS `.m3u8` playlists & MPD DASH\n"
        "• AppX / Classplus signed URL endpoints\n"
        "• YouTube, Vimeo, and 1000+ yt-dlp sites\n\n"
        "When you send a `.txt` file, choose a start index (e.g. `1` or `15`) or range (`1-10`)."
    )

async def thumb_command(client: Client, message: Message):
    user_id = message.from_user.id
    thumb = USER_THUMBNAILS.get(user_id)
    if thumb and os.path.isfile(thumb):
        await message.reply_photo(photo=thumb, caption="🖼️ Current thumbnail. Send `/delthumb` to remove.")
    else:
        await message.reply_text("ℹ️ No custom thumbnail set. Send a photo to set one.")

async def delthumb_command(client: Client, message: Message):
    user_id = message.from_user.id
    thumb = USER_THUMBNAILS.pop(user_id, None)
    if thumb and os.path.isfile(thumb):
        try:
            os.remove(thumb)
        except Exception:
            pass
        await message.reply_text("🗑️ Custom thumbnail deleted.")
    else:
        await message.reply_text("ℹ️ No custom thumbnail to delete.")

async def photo_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if not is_authorized(user_id):
        return
    os.makedirs(Config.THUMB_DIR, exist_ok=True)
    thumb_path = os.path.join(Config.THUMB_DIR, f"thumb_{user_id}.jpg")
    status = await message.reply_text("⏳ Saving thumbnail...")
    try:
        await message.download(file_name=thumb_path)
        USER_THUMBNAILS[user_id] = thumb_path
        await status.edit_text("✅ Custom thumbnail saved!")
    except Exception as e:
        await status.edit_text(f"❌ Failed: {e}")

async def cancel_command(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in ACTIVE_TASKS and ACTIVE_TASKS[user_id].get("active", False):
        ACTIVE_TASKS[user_id]["cancel"] = True
        await message.reply_text("🛑 Cancellation received. Stopping after current task...")
    else:
        await message.reply_text("ℹ️ No active download running.")

async def stats_command(client: Client, message: Message):
    total, used, free = shutil.disk_usage(Config.DOWNLOAD_DIR if os.path.exists(Config.DOWNLOAD_DIR) else ".")
    active = sum(1 for t in ACTIVE_TASKS.values() if t.get("active", False))
    await message.reply_text(
        f"📊 **System Status:**\n\n"
        f"• **Active Tasks:** `{active}`\n"
        f"• **Disk Total:** `{MediaHelper.format_size(total)}`\n"
        f"• **Disk Free:** `{MediaHelper.format_size(free)}`"
    )
