import os
import sys
import asyncio
import logging
from pyrogram import Client, filters
from pyrogram.handlers import MessageHandler
from config import Config

from handlers.commands import (
    start_command,
    help_command,
    thumb_command,
    delthumb_command,
    photo_handler,
    cancel_command,
    stats_command,
)
from handlers.text_handler import (
    txt_document_handler,
    text_response_handler,
)
from web import start_web_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("TextLeechBot")

def check_credentials():
    missing = []
    if not Config.API_ID or Config.API_ID == 0:
        missing.append("API_ID")
    if not Config.API_HASH:
        missing.append("API_HASH")
    if not Config.BOT_TOKEN:
        missing.append("BOT_TOKEN")

    if missing:
        logger.error(f"Missing required environment variables: {', '.join(missing)}")
        logger.error("Please configure them in Render Environment Variables.")
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

    # Command Handlers
    app.add_handler(MessageHandler(start_command, filters.command(["start"]) & filters.private))
    app.add_handler(MessageHandler(help_command, filters.command(["help"]) & filters.private))
    app.add_handler(MessageHandler(thumb_command, filters.command(["thumb"]) & filters.private))
    app.add_handler(MessageHandler(delthumb_command, filters.command(["delthumb"]) & filters.private))
    app.add_handler(MessageHandler(cancel_command, filters.command(["cancel", "stop"]) & filters.private))
    app.add_handler(MessageHandler(stats_command, filters.command(["stats"]) & filters.private))
    app.add_handler(MessageHandler(photo_handler, filters.photo & filters.private))
    app.add_handler(MessageHandler(txt_document_handler, filters.document & filters.private))
    
    # Text Message Handler (Matches plain text in private chats, excluding slash commands)
    app.add_handler(MessageHandler(text_response_handler, filters.text & filters.private & ~filters.regex(r"^/")))

    # Health check web server for Render keep-alive
    web_runner = None
    if Config.WEB_SERVER:
        web_runner = await start_web_server()

    logger.info("Starting Telegram Bot...")
    await app.start()
    bot_info = await app.get_me()
    logger.info(f"Bot connected successfully as @{bot_info.username} (ID: {bot_info.id})")

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received...")
    finally:
        if app.is_connected:
            await app.stop()
        if web_runner:
            await web_runner.cleanup()
        logger.info("Bot stopped cleanly.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
