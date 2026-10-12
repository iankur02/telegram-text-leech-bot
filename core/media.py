import os
import json
import logging
import subprocess
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class MediaHelper:
    @staticmethod
    def get_video_metadata(video_path: str) -> Tuple[int, int, int]:
        default_metadata = (0, 1280, 720)
        if not video_path or not os.path.isfile(video_path):
            logger.warning(f"Metadata requested for non-existent file: {video_path}")
            return default_metadata

        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration:stream=width,height",
                "-of", "json",
                video_path
            ]
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=12
            )

            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                duration = 0
                format_info = data.get("format", {})
                if "duration" in format_info:
                    try:
                        duration = int(float(format_info["duration"]))
                    except (ValueError, TypeError):
                        duration = 0

                width, height = 1280, 720
                streams = data.get("streams", [])
                for stream in streams:
                    if "width" in stream and "height" in stream:
                        try:
                            width = int(stream["width"])
                            height = int(stream["height"])
                            break
                        except (ValueError, TypeError):
                            continue

                return duration, width, height
            return default_metadata

        except Exception as e:
            logger.warning(f"ffprobe extraction fallback triggered: {e}")
            return default_metadata

    @staticmethod
    def generate_thumbnail(video_path: str, thumb_path: str, duration: int = 0) -> Optional[str]:
        if not video_path or not os.path.isfile(video_path):
            return None

        os.makedirs(os.path.dirname(os.path.abspath(thumb_path)), exist_ok=True)

        try:
            seek_pos = max(1, int(duration * 0.10)) if duration > 0 else 1
            cmd = [
                "ffmpeg",
                "-ss", str(seek_pos),
                "-i", video_path,
                "-vframes", "1",
                "-vf", "scale=320:-1",
                "-q:v", "2",
                thumb_path,
                "-y"
            ]
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15
            )

            if os.path.isfile(thumb_path) and os.path.getsize(thumb_path) > 0:
                return thumb_path
        except Exception as e:
            logger.warning(f"Thumbnail generation failed: {e}")

        return None

    @staticmethod
    def format_duration(seconds: int) -> str:
        if not seconds or seconds < 0:
            return "00:00"
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

    @staticmethod
    def format_size(bytes_count: int) -> str:
        if not bytes_count:
            return "0 B"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_count < 1024.0:
                return f"{bytes_count:.2f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.2f} PB"
