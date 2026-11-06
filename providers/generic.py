import asyncio
from typing import List, Dict, Any
from .base import BaseProvider
import yt_dlp
import logging

logger = logging.getLogger(__name__)

class GenericProvider(BaseProvider):
    async def can_handle(self, url: str) -> bool:
        u = url.strip().strip("<>").lower()
        if not (u.startswith("http://") or u.startswith("https://")):
            return False
        # If it's a known specialized platform, let their dedicated providers handle it
        if "zee5.com" in u or "net79" in u or "netmirror" in u:
            return False
        return True

    async def get_metadata(self, url: str) -> Dict[str, Any]:
        clean_url = url.strip().strip("<>")
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "extract_flat": False,
        }
        loop = asyncio.get_running_loop()

        def _extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(clean_url, download=False)

        try:
            info = await loop.run_in_executor(None, _extract)
            return {
                "title": info.get("title") or clean_url.split("/")[-1].split("?")[0] or "Media Stream",
                "poster": info.get("thumbnail"),
                "provider": info.get("extractor_key", "Direct / Generic"),
                "ext": info.get("ext", "mp4"),
                "size": str(info.get("filesize_approx") or info.get("filesize") or "Auto"),
                "duration": info.get("duration"),
                "url": clean_url
            }
        except Exception as e:
            logger.warning(f"yt-dlp metadata fallback for {clean_url}: {e}")
            return {
                "title": clean_url.split("/")[-1].split("?")[0] or "Media Stream",
                "poster": None,
                "provider": "Direct Link",
                "ext": clean_url.split(".")[-1].split("?")[0] if "." in clean_url else "mp4",
                "size": "Direct Stream",
                "url": clean_url
            }

    async def get_formats(self, url: str) -> List[Dict[str, Any]]:
        clean_url = url.strip().strip("<>")
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
        }
        loop = asyncio.get_running_loop()

        def _extract():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(clean_url, download=False)

        try:
            info = await loop.run_in_executor(None, _extract)
            raw_formats = info.get("formats", [])
            formats = []
            seen_res = set()

            for f in raw_formats:
                height = f.get("height")
                format_id = f.get("format_id")
                if height and height not in seen_res:
                    seen_res.add(height)
                    note = f.get("format_note", "") or f.get("ext", "mp4")
                    formats.append({
                        "format_id": str(format_id),
                        "resolution": f"{height}p",
                        "note": str(note),
                        "url": f.get("url")
                    })

            # Sort by resolution descending if available
            formats.sort(key=lambda x: int(x["resolution"].replace("p", "")) if x["resolution"].replace("p", "").isdigit() else 0, reverse=True)

            if not formats:
                formats.append({
                    "format_id": "best",
                    "resolution": "Original",
                    "note": str(info.get("ext", "Direct")),
                    "url": clean_url
                })
            return formats
        except Exception as e:
            logger.warning(f"yt-dlp format fallback for {clean_url}: {e}")
            return [{
                "format_id": "direct",
                "resolution": "Direct",
                "note": "Stream URL",
                "url": clean_url
            }]

    async def get_download_url(self, format_id: str, metadata: Dict[str, Any]) -> str:
        return metadata.get("url", "")
