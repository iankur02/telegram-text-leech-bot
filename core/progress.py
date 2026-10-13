import time
import math
import re
import asyncio
import logging
from config import Config
from core.media import MediaHelper

logger = logging.getLogger(__name__)


class ProgressTracker:
    def __init__(self, status_message, action_name: str = "Uploading"):
        self.status_message = status_message
        self.action_name = action_name
        self.start_time = time.time()
        self.last_update_time = 0
        self.interval = Config.PROGRESS_UPDATE_INTERVAL

    async def update(self, current: int, total: int):
        now = time.time()
        if (now - self.last_update_time) < self.interval and current < total:
            return

        self.last_update_time = now
        elapsed_time = max(1, round(now - self.start_time))
        percentage = current * 100 / total if total > 0 else 0
        speed = current / elapsed_time
        time_to_completion = round((total - current) / speed) if speed > 0 else 0

        bar_len = 10
        filled = math.floor(percentage / (100 / bar_len))
        bar = "█" * filled + "░" * (bar_len - filled)

        text = (
            f"⚡ **{self.action_name}...**\n\n"
            f"`[{bar}]` **{percentage:.1f}%**\n\n"
            f"📦 **Size:** `{MediaHelper.format_size(current)} / {MediaHelper.format_size(total)}`\n"
            f"🚀 **Speed:** `{MediaHelper.format_size(int(speed))}/s`\n"
            f"⏳ **ETA:** `{MediaHelper.format_duration(time_to_completion)}`"
        )

        try:
            await self.status_message.edit_text(text)
        except Exception as e:
            err_str = str(e).lower()
            if "flood" in err_str:
                match = re.search(r"(\d+)", str(e))
                wait = int(match.group(1)) if match else 5
                await asyncio.sleep(min(wait, 60))
            else:
                logger.debug(f"Progress edit failed: {e}")
