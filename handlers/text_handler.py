import os
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from config import Config
from core.parser import TextParser
from core.downloader import VideoDownloader
from core.uploader import VideoUploader
from handlers.commands import is_authorized, ACTIVE_TASKS, USER_THUMBNAILS, PENDING_CONFIG

logger = logging.getLogger(__name__)

async def txt_document_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if not is_authorized(user_id):
        await message.reply_text("⛔ Access Denied.")
        return

    doc = message.document
    if not doc or not (doc.file_name.endswith(".txt") or doc.mime_type == "text/plain"):
        await message.reply_text("⚠️ Please send a valid `.txt` file.")
        return

    if user_id in ACTIVE_TASKS and ACTIVE_TASKS[user_id].get("active", False):
        await message.reply_text("⚠️ A task is already active. Send `/cancel` to stop it.")
        return

    status = await message.reply_text("📥 Parsing `.txt` file...")
    os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
    temp_txt_path = os.path.join(Config.DOWNLOAD_DIR, f"input_{user_id}_{doc.file_name}")

    try:
        await message.download(file_name=temp_txt_path)
        items = TextParser.parse_file(temp_txt_path)
    finally:
        if os.path.isfile(temp_txt_path):
            os.remove(temp_txt_path)

    if not items:
        await status.edit_text("❌ No valid video URLs found in file.")
        return

    PENDING_CONFIG[user_id] = items
    await status.edit_text(
        f"📄 **Text File Analyzed!**\n\n"
        f"🔗 **Total valid links:** `{len(items)}`\n"
        f"• **First:** `{items[0]['raw_title']}`\n"
        f"• **Last:** `{items[-1]['raw_title']}`\n\n"
        f"Reply with:\n"
        f"• `1` or `all` : Process all\n"
        f"• `15` : Start from #15\n"
        f"• `1-10` : Process range 1 to 10\n"
        f"• Optional quality: `1 720` or `1 480`"
    )

async def text_response_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if not is_authorized(user_id) or user_id not in PENDING_CONFIG:
        return

    all_items = PENDING_CONFIG.pop(user_id)
    tokens = message.text.strip().lower().split()

    start_idx = 1
    end_idx = None
    quality = "720"

    if tokens:
        range_part = tokens[0]
        if range_part not in ("all", "start"):
            if "-" in range_part:
                try:
                    s_str, e_str = range_part.split("-", 1)
                    start_idx = int(s_str.strip())
                    end_idx = int(e_str.strip())
                except ValueError:
                    start_idx = 1
            elif range_part.isdigit():
                start_idx = int(range_part)

        if len(tokens) > 1 and (tokens[1].isdigit() or tokens[1] in ("best", "480", "720", "360", "1080")):
            quality = tokens[1]

    selected_items = [
        it for it in all_items 
        if it["index"] >= start_idx and (end_idx is None or it["index"] <= end_idx)
    ]

    if not selected_items:
        await message.reply_text("⚠️ No items matched that range.")
        return

    ACTIVE_TASKS[user_id] = {"active": True, "cancel": False}
    asyncio.create_task(
        execute_batch(client, message.chat.id, user_id, selected_items, quality)
    )

async def execute_batch(client: Client, chat_id: int, user_id: int, items: list, quality: str):
    total = len(items)
    status_msg = await client.send_message(chat_id, f"🚀 Starting batch of {total} videos ({quality}p)...")
    success_count, fail_count = 0, 0
    custom_thumb = USER_THUMBNAILS.get(user_id)

    for i, item in enumerate(items, 1):
        if user_id in ACTIVE_TASKS and ACTIVE_TASKS[user_id].get("cancel", False):
            await status_msg.edit_text("🛑 Batch cancelled by user.")
            break

        idx_str = f"[{i}/{total}]"
        title = item["title"]

        try:
            await status_msg.edit_text(
                f"📥 **Downloading {idx_str}**\n\n"
                f"**Name »** `{title}`\n"
                f"**Quality »** `{quality}p`"
            )
        except Exception:
            pass

        result = await VideoDownloader.download(item["url"], item["safe_filename"], quality=quality)

        if not result.success or not result.file_path or not os.path.isfile(result.file_path):
            fail_count += 1
            await client.send_message(chat_id, f"❌ **Failed {idx_str}:** `{title}`\nReason: `{result.error}`")
            continue

        try:
            await status_msg.edit_text(f"📤 **Uploading {idx_str}**\n\n`{title}`")
        except Exception:
            pass

        ok = await VideoUploader.upload(client, chat_id, result.file_path, title, status_msg, custom_thumb)
        if ok:
            success_count += 1
        else:
            fail_count += 1

        await asyncio.sleep(2)

    ACTIVE_TASKS[user_id] = {"active": False, "cancel": False}
    await status_msg.edit_text(
        f"🏁 **Batch Complete!**\n\n"
        f"✅ **Uploaded:** `{success_count}`\n"
        f"❌ **Failed:** `{fail_count}`\n"
        f"📊 **Total:** `{total}`"
    )
