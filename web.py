import os
import logging
from aiohttp import web
from config import Config

logger = logging.getLogger(__name__)

async def handle_index(request):
    return web.json_response({
        "status": "online",
        "bot": "Telegram Text Leech Bot",
        "service": "Render Web Service",
        "health": "healthy"
    })

async def handle_health(request):
    return web.Response(text="OK", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/health", handle_health)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, "0.0.0.0", Config.PORT)
    await site.start()
    logger.info(f"Render Web Health Server listening on 0.0.0.0:{Config.PORT}")
    return runner
