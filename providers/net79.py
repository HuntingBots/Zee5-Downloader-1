from .base import BaseProvider
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class Net79Provider(BaseProvider):
    def __init__(self):
        self.base_url = "https://net79.cc/"

    async def can_handle(self, url: str) -> bool:
        u = url.strip().strip("<>").lower()
        return "net79" in u or "netmirror" in u or "cineby" in u

    async def get_metadata(self, url: str) -> Dict[str, Any]:
        clean_url = url.strip().strip("<>")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(clean_url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    title_elem = soup.select_one('h1.title') or soup.select_one('h1') or soup.select_one('title')
                    title = title_elem.text.strip() if title_elem else clean_url.split("/")[-1] or "Net79 Media"
                    
                    poster_elem = soup.select_one('img.poster') or soup.select_one('meta[property="og:image"]')
                    poster = None
                    if poster_elem:
                        poster = poster_elem.get('src') or poster_elem.get('content')
                    
                    return {
                        "title": title,
                        "poster": poster,
                        "provider": "Net79 / NetMirror",
                        "ext": "mp4",
                        "size": "Auto",
                        "url": clean_url
                    }
        except Exception as e:
            logger.error(f"Net79 get_metadata error: {e}")
            return {
                "title": clean_url.split("/")[-1] or "Net79 Media",
                "poster": None,
                "provider": "Net79 / NetMirror",
                "ext": "mp4",
                "size": "Unknown",
                "url": clean_url
            }

    async def get_formats(self, url: str) -> List[Dict[str, Any]]:
        clean_url = url.strip().strip("<>")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(clean_url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    formats = []
                    sources = soup.select('video source')
                    for src in sources:
                        res = src.get('size', '720')
                        src_url = src.get('src', '')
                        if src_url:
                            formats.append({
                                "format_id": src_url,
                                "resolution": f"{res}p" if not str(res).endswith('p') else str(res),
                                "note": "Direct Stream",
                                "url": src_url
                            })
                    return formats if formats else [{"format_id": "default", "resolution": "720p", "note": "Default Stream", "url": clean_url}]
        except Exception as e:
            logger.error(f"Net79 get_formats error: {e}")
            return [{"format_id": "default", "resolution": "720p", "note": "Default Stream", "url": clean_url}]

    async def get_download_url(self, format_id: str, metadata: Dict[str, Any]) -> str:
        return format_id if format_id != "default" else metadata.get("url", "")
