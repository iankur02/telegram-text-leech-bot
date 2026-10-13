import os
import re
import json
import logging
import asyncio
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


URL_IN_TEXT = re.compile(r'https?://[^\s"\'\\<>\)\]]+', re.IGNORECASE)


class VideoDownloader:
    PRIORITY_KEYS = (
        "video_url", "videoUrl", "video_player", "videoPlayer",
        "stream_url", "streamUrl", "hls_url", "hlsUrl",
        "dash_url", "dashUrl", "play_url", "playUrl",
        "download_url", "downloadUrl", "file_url", "fileUrl",
        "url", "link", "src", "file", "mp4", "hls", "m3u8",
    )

    # ---------- helpers ----------

    @staticmethod
    def _looks_like_media_url(s: str) -> bool:
        if not isinstance(s, str) or not s.startswith("http"):
            return False
        low = s.lower()
        return any(t in low for t in [
            ".m3u8", ".mp4", ".mpd", ".mkv", ".webm",
            "/hls/", "/dash/", "master.m3u8", "manifest",
        ])

    @classmethod
    def _extract_url_from_json(cls, data: Any, depth: int = 0) -> Optional[str]:
        if depth > 6:
            return None
        if isinstance(data, str):
            if cls._looks_like_media_url(data):
                return data
            stripped = data.strip()
            if stripped.startswith("{") or stripped.startswith("["):
                try:
                    return cls._extract_url_from_json(json.loads(stripped), depth + 1)
                except Exception:
                    pass
            for m in URL_IN_TEXT.findall(data):
                m = m.replace("\\/", "/")
                if cls._looks_like_media_url(m):
                    return m
            return None
        if isinstance(data, list):
            for item in data:
                found = cls._extract_url_from_json(item, depth + 1)
                if found:
                    return found
            return None
        if isinstance(data, dict):
            for key in cls.PRIORITY_KEYS:
                if key in data:
                    found = cls._extract_url_from_json(data[key], depth + 1)
                    if found:
                        return found
            for k, v in data.items():
                if k in ("status", "success", "message", "msg", "error", "code"):
                    continue
                found = cls._extract_url_from_json(v, depth + 1)
                if found:
                    return found
        return None

    @classmethod
    def resolve_url(cls, url: str, headers: Optional[Dict[str, str]] = None) -> Tuple[str, Dict[str, str]]:
        req_headers = {
            "User-Agent": Config.USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if headers:
            req_headers.update(headers)

        parsed = urlparse(url)
        req_headers.setdefault("Referer", f"{parsed.scheme}://{parsed.netloc}/")

        # Only try to pre-resolve endpoints that act as a "sign URL" proxy.
        if any(k in url.lower() for k in [
            "fetch_video", "get_video", "sign_url", "api_base=",
            "sign-urls", "video_url", "get-url", "extract", "player",
        ]):
            try:
                session = requests.Session()
                session.headers.update(req_headers)
                resp = session.get(url, allow_redirects=True, timeout=25)

                cookie_str = "; ".join(f"{c.name}={c.value}" for c in session.cookies)
                if cookie_str:
                    req_headers["Cookie"] = cookie_str

                # 1) Redirect straight to a media file
                if resp.url != url and cls._looks_like_media_url(resp.url):
                    logger.info(f"Resolved via redirect -> {resp.url[:140]}")
                    return resp.url, req_headers

                content_type = resp.headers.get("Content-Type", "").lower()
                text = resp.text or ""

                # 2) Endpoint returned a raw m3u8 manifest
                if "#EXTM3U" in text[:500]:
                    logger.info("Endpoint returned raw m3u8")
                    return resp.url, req_headers

                # 3) JSON body
                if "json" in content_type or text.strip().startswith("{"):
                    try:
                        data = resp.json()
                        found = cls._extract_url_from_json(data)
                        if found:
                            logger.info(f"Resolved via JSON -> {found[:140]}")
                            return found, req_headers
                    except Exception as e:
                        logger.debug(f"JSON parse failed: {e}")

                # 4) Regex over the raw body (escaped JSON / HTML)
                for m in URL_IN_TEXT.findall(text):
                    m = m.replace("\\/", "/").rstrip('",\'')
                    if cls._looks_like_media_url(m):
                        logger.info(f"Resolved via regex -> {m[:140]}")
                        return m, req_headers

            except Exception as e:
                logger.warning(f"URL pre-resolution exception: {e}")

        return url, req_headers

    # ---------- main downloader ----------

    @classmethod
    async def download(
        cls,
        url: str,
        output_filename: str,
        quality: str = "720",
        progress_callback=None,
        headers: Optional[Dict[str, str]] = None,
    ) -> DownloadResult:
        os.makedirs(Config.DOWNLOAD_DIR, exist_ok=True)
        base_output_path = os.path.join(Config.DOWNLOAD_DIR, output_filename)
        expected_output_mp4 = f"{base_output_path}.mp4"

        # Clean leftovers from previous runs
        for ext in [".mp4", ".mkv", ".webm", ".mp4.part", ".ytdl", ".ts"]:
            p = f"{base_output_path}{ext}"
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

        resolved_url, req_headers = cls.resolve_url(url, headers)
        parsed = urlparse(resolved_url)
        referer = req_headers.get("Referer", f"{parsed.scheme}://{parsed.netloc}/")
        origin = f"{parsed.scheme}://{parsed.netloc}"

        ytdl_error = None

        # ---------- Attempt 1: yt-dlp ----------
        try:
            if quality.isdigit():
                format_spec = (
                    f"bestvideo[height<={quality}]+bestaudio/"
                    f"best[height<={quality}]/best"
                )
            else:
                format_spec = "bestvideo+bestaudio/best"

            ytdl_cmd = [
                "yt-dlp",
                "--no-check-certificates",
                "--no-warnings",
                "--retries", "10",
                "--fragment-retries", "20",
                "--socket-timeout", "30",
                "--concurrent-fragments", "4",
                "--hls-prefer-native",
                "--user-agent", Config.USER_AGENT,
                "--referer", referer,
                "--add-header", f"Origin: {origin}",
                "--add-header", "Accept: */*",
                "--merge-output-format", "mp4",
                "-f", format_spec,
                "-o", expected_output_mp4,
            ]
            if req_headers.get("Cookie"):
                ytdl_cmd.extend(["--add-header", f"Cookie: {req_headers['Cookie']}"])

            ytdl_cmd.append(resolved_url)

            logger.info(f"[yt-dlp] {resolved_url[:140]}")

            process = await asyncio.create_subprocess_exec(
                *ytdl_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if (
                process.returncode == 0
                and os.path.exists(expected_output_mp4)
                and os.path.getsize(expected_output_mp4) > 10240
            ):
                return DownloadResult(success=True, file_path=expected_output_mp4)

            ytdl_error = (
                stderr.decode("utf-8", errors="ignore")
                or stdout.decode("utf-8", errors="ignore")
            ).strip()
            if ytdl_error:
                logger.warning(f"yt-dlp stderr tail: {ytdl_error[-500:]}")
        except Exception as e:
            ytdl_error = str(e)
            logger.warning(f"yt-dlp exception: {e}")

        # ---------- Attempt 2: ffmpeg (HLS / DASH) ----------
        try:
            ffmpeg_headers = (
                f"User-Agent: {Config.USER_AGENT}\r\n"
                f"Referer: {referer}\r\n"
                f"Origin: {origin}\r\n"
            )
            if req_headers.get("Cookie"):
                ffmpeg_headers += f"Cookie: {req_headers['Cookie']}\r\n"

            ffmpeg_cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel", "error",
                "-headers", ffmpeg_headers,
                "-user_agent", Config.USER_AGENT,
                "-i", resolved_url,
                "-c", "copy",
                "-bsf:a", "aac_adtstoasc",
                "-movflags", "+faststart",
                expected_output_mp4,
                "-y",
            ]
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if (
                process.returncode == 0
                and os.path.exists(expected_output_mp4)
                and os.path.getsize(expected_output_mp4) > 10240
            ):
                return DownloadResult(success=True, file_path=expected_output_mp4)

            err = stderr.decode("utf-8", errors="ignore").strip()
            if err:
                logger.warning(f"ffmpeg stderr tail: {err[-500:]}")
        except Exception as e:
            logger.warning(f"FFmpeg fallback failed: {e}")

        # ---------- Cleanup ----------
        for ext in [".part", ".ytdl"]:
            p = f"{expected_output_mp4}{ext}"
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

        clean_error = ytdl_error or "Download was interrupted or stream unavailable"
        if "403" in clean_error:
            clean_error = "HTTP 403 Forbidden (link/token expired or IP blocked)"
        elif "404" in clean_error:
            clean_error = "HTTP 404 Not Found"
        elif "410" in clean_error:
            clean_error = "HTTP 410 Gone (link expired)"
        return DownloadResult(success=False, error=clean_error[:300])
