import os
import re
import asyncio
import logging
from typing import Optional
from pyrogram.errors import FloodWait, RPCError
from config import Config
from core.media import MediaHelper
from core.progress import ProgressTracker

logger = logging.getLogger(__name__)

class VideoUploader:
    @classmethod
    async def upload(
        cls,
        client,
        chat_id: int,
        video_path: str,
        title: str,
        status_message,
        custom_thumb: Optional[str] = None
    ) -> bool:
        if not video_path or not os.path.isfile(video_path) or os.path.getsize(video_path) == 0:
            return False

        file_size = os.path.getsize(video_path)
        duration, width, height = MediaHelper.get_video_metadata(video_path)
        
        temp_thumb = None
        if custom_thumb and os.path.isfile(custom_thumb):
            thumb_path = custom_thumb
        else:
            temp_thumb = f"{video_path}.thumb.jpg"
            thumb_path = MediaHelper.generate_thumbnail(video_path, temp_thumb, duration)

        caption = (
            f"🎬 **{title}**\n\n"
            f"⏱️ **Duration:** `{MediaHelper.format_duration(duration)}`\n"
            f"📦 **Size:** `{MediaHelper.format_size(file_size)}`\n"
            f"🖥️ **Resolution:** `{width}x{height}`"
        )

        progress = ProgressTracker(status_message, action_name="Uploading")
        success = False

        for attempt in range(3):
            try:
                sent_msg = await client.send_video(
                    chat_id=chat_id,
                    video=video_path,
                    caption=caption,
                    duration=duration,
                    width=width,
                    height=height,
                    thumb=thumb_path if (thumb_path and os.path.isfile(thumb_path)) else None,
                    supports_streaming=True,
                    progress=progress.update
                )
                if Config.DUMP_CHANNEL and Config.DUMP_CHANNEL != 0:
                    try:
                        await sent_msg.copy(Config.DUMP_CHANNEL)
                    except Exception:
                        pass
                success = True
                break
            except FloodWait as e:
                await asyncio.sleep(e.value + 1)
            except RPCError as e:
                logger.error(f"Telegram RPC error: {e}")
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"Upload error: {e}")
                break

        # Immediate cleanup
        try:
            if os.path.isfile(video_path):
                os.remove(video_path)
            if temp_thumb and os.path.isfile(temp_thumb):
                os.remove(temp_thumb)
        except Exception:
            pass

        return success
