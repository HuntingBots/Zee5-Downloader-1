import aiohttp
import re
from providers.base import BaseProvider
from typing import List, Dict, Any

class GenericProvider(BaseProvider):
    async def can_handle(self, url: str) -> bool:
        # Simple check for common media extensions or generic URLs
        return any(ext in url.lower() for ext in [".m3u8", ".mp4", ".mkv", ".mp3"])

    async def get_metadata(self, url: str) -> Dict[str, Any]:
        # In a real scenario, we might scrape the page or use an API
        # For generic, we just return basic info
        return {
            "title": url.split("/")[-1].split("?")[0] or "Generic Media",
            "provider": "Generic",
            "url": url,
            "poster": "https://via.placeholder.com/500x750?text=No+Poster"
        }

    async def get_formats(self, url: str) -> List[Dict[str, Any]]:
        # For generic, we might just return the original URL as a format
        # Or parse the M3U8 if it's a master playlist
        return [
            {
                "format_id": "original",
                "resolution": "Unknown",
                "ext": url.split(".")[-1].split("?")[0] if "." in url else "mp4",
                "note": "Original Quality",
                "url": url
            }
        ]

    async def get_download_url(self, format_id: str, metadata: Dict[str, Any]) -> str:
        return metadata["url"]
