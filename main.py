import os
import sys
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from config import Config
from handlers import (
    start_command,
    help_command,
    thumb_command,
    delthumb_command,
    photo_handler,
    cancel_command,
    stats_command,
    txt_document_handler,
    text_response_handler
)
from web import start_web_server

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("TextLeechBot")

def check_credentials():
    missing = [k for k, v in [("36629816", Config.API_ID), ("b074123de6def8946d6bce8b4fff699a", Config.API_HASH), ("BOT_TOKEN", Config.BOT_TOKEN)] if not v]
    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        sys.exit(1)

async def main():
    check_credentials()
    os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
    os.makedirs(Config.THUMB_DIR, exist_ok=True)

    app = Client(
        name="text_leech_bot",
        api_id=Config.API_ID,
        api_hash=Config.API_HASH,
        bot_token=Config.BOT_TOKEN,
        workdir=Config.DOWNLOAD_DIR
    )

    app.add_handler(MessageHandler(start_command, filters.command(["start"]) & filters.private))
    app.add_handler(MessageHandler(help_command, filters.command(["help"]) & filters.private))
    app.add_handler(MessageHandler(thumb_command, filters.command(["thumb"]) & filters.private))
    app.add_handler(MessageHandler(delthumb_command, filters.command(["delthumb"]) & filters.private))
    app.add_handler(MessageHandler(cancel_command, filters.command(["cancel", "stop"]) & filters.private))
    app.add_handler(MessageHandler(stats_command, filters.command(["stats"]) & filters.private))
    app.add_handler(MessageHandler(photo_handler, filters.photo & filters.private))
    app.add_handler(MessageHandler(txt_document_handler, filters.document & filters.private))
    app.add_handler(MessageHandler(text_response_handler, filters.text & ~filters.command & filters.private))

    web_runner = None
    if Config.WEB_SERVER:
        web_runner = await start_web_server()

    logger.info("Starting Telegram Bot...")
    await app.start()
    bot_info = await app.get_me()
    logger.info(f"Bot connected: @{bot_info.username}")

    try:
        await asyncio.Event().wait()
    finally:
        if app.is_connected:
            await app.stop()
        if web_runner:
            await web_runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
