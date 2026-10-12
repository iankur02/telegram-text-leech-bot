import os
import re
import json
import logging
import asyncio
import subprocess
from typing import Optional, Tuple, Dict, Any
from urllib.parse import urlparse
import requests
from config import Config

logger = logging.getLogger(__name__)

class DownloadResult:
    def __init__(self, success: bool, file_path: Optional[str] = None, error: Optional[str] = None):
        self.success = success
        self.file_path = file_path
        self.error = error

class VideoDownloader:
    @staticmethod
    def resolve_url(url: str, headers: Optional[Dict[str, str]] = None) -> Tuple[str, Dict[str, str]]:
        req_headers = {
            "User-Agent": Config.USER_AGENT,
            "Accept": "*/*",
        }
        if headers:
            req_headers.update(headers)

        parsed = urlparse(url)
        referer = f"{parsed.scheme}://{parsed.netloc}/"
        req_headers["Referer"] = referer

        if any(k in url.lower() for k in ["fetch_video", "get_video", "sign_url", "api_base="]):
            try:
                resp = requests.get(url, headers=req_headers, allow_redirects=True, timeout=20)
                if resp.url != url:
                    final_url = resp.url
                    if any(ext in final_url.lower() for ext in [".m3u8", ".mp4", ".mpd", ".mkv"]):
                        return final_url, req_headers

                content_type = resp.headers.get("Content-Type", "").lower()
                text_preview = resp.text.strip()
                if "application/json" in content_type or (text_preview.startswith("{") and text_preview.endswith("}")):
                    data = resp.json()
                    for key in ["url", "video_url", "stream_url", "link", "download_url", "hls_url", "file_url"]:
                        if key in data and isinstance(data[key], str) and data[key].startswith("http"):
                            return data[key], req_headers

                    if "data" in data and isinstance(data["data"], dict):
                        for key in ["url", "video_url", "stream_url", "link", "hls"]:
                            if key in data["data"] and isinstance(data["data"][key], str) and data["data"][key].startswith("http"):
                                return data["data"][key], req_headers
            except Exception as e:
                logger.warning(f"URL pre-resolution exception: {e}")

        return url, req_headers

    @classmethod
    async def download(
        cls,
        url: str,
        output_filename: str,
        quality: str = "720",
        progress_callback=None,
        headers: Optional[Dict[str, str]] = None
    ) -> DownloadResult:
        os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
        base_output_path = os.path.join(Config.DOWNLOAD_DIR, output_filename)
        expected_output_mp4 = f"{base_output_path}.mp4"

        for ext in [".mp4", ".mkv", ".webm", ".mp4.part", ".ytdl"]:
            p = f"{base_output_path}{ext}"
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

        resolved_url, req_headers = cls.resolve_url(url, headers)
        parsed = urlparse(resolved_url)
        referer = req_headers.get("Referer", f"{parsed.scheme}://{parsed.netloc}/")

        ytdl_error = None
        try:
            format_spec = f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best" if quality.isdigit() else "bestvideo+bestaudio/best"

            ytdl_cmd = [
                "yt-dlp",
                "--no-check-certificates",
                "--no-warnings",
                "--retries", "5",
                "--fragment-retries", "10",
                "--user-agent", Config.USER_AGENT,
                "--referer", referer,
                "-f", format_spec,
                "--merge-output-format", "mp4",
                "-o", expected_output_mp4,
                resolved_url
            ]

            process = await asyncio.create_subprocess_exec(
                *ytdl_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0 and os.path.exists(expected_output_mp4) and os.path.getsize(expected_output_mp4) > 1024:
                return DownloadResult(success=True, file_path=expected_output_mp4)
            else:
                ytdl_error = stderr.decode('utf-8', errors='ignore').strip() or stdout.decode('utf-8', errors='ignore').strip()

        except Exception as e:
            ytdl_error = str(e)

        # FFMPEG fallback for HLS/m3u8
        if ".m3u8" in resolved_url.lower() or "stream" in resolved_url.lower() or not os.path.exists(expected_output_mp4):
            try:
                ffmpeg_headers = f"User-Agent: {Config.USER_AGENT}\r\nReferer: {referer}\r\n"
                ffmpeg_cmd = [
                    "ffmpeg",
                    "-headers", ffmpeg_headers,
                    "-i", resolved_url,
                    "-c", "copy",
                    "-bsf:a", "aac_adtstoasc",
                    expected_output_mp4,
                    "-y"
                ]
                process = await asyncio.create_subprocess_exec(
                    *ffmpeg_cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate()
                if process.returncode == 0 and os.path.exists(expected_output_mp4) and os.path.getsize(expected_output_mp4) > 1024:
                    return DownloadResult(success=True, file_path=expected_output_mp4)
            except Exception as e:
                logger.warning(f"FFmpeg fallback failed: {e}")

        # Clean partial artifacts
        for ext in [".part", ".ytdl"]:
            p = f"{expected_output_mp4}{ext}"
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

        clean_error = ytdl_error or "Download was interrupted or stream unavailable"
        if "403" in clean_error:
            clean_error = "HTTP 403 Forbidden (Link expired or token invalid)"
        elif "404" in clean_error:
            clean_error = "HTTP 404 Not Found"
        return DownloadResult(success=False, error=clean_error[:150])
