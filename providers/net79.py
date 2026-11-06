from .base import BaseProvider
import aiohttp
import asyncio
import os
import re
import time
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)

class Net79Provider(BaseProvider):
    def __init__(self):
        self.base_url = "https://net79.cc"
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://net79.cc/"
        }

    async def can_handle(self, url: str) -> bool:
        u = url.strip().strip("<>\"' ").lower()
        return "net79" in u or "netmirror" in u or "cineby" in u

    async def search(self, query: str) -> List[Dict[str, Any]]:
        """Search titles on NetMirror / Net79 catalog."""
        clean_q = query.strip()
        url = f"{self.base_url}/api/catalog/search-hybrid?q={aiohttp.helpers.quote(clean_q, safe='')}"
        try:
            async with aiohttp.ClientSession(headers=self.default_headers) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        logger.error(f"Search failed with status {resp.status}")
                        return []
                    data = await resp.json()
                    return data.get("items", [])
        except Exception as e:
            logger.error(f"Error searching Net79: {e}")
            return []

    async def get_title_details(self, tmdb_id: int, media_type: str = "tv") -> Dict[str, Any]:
        """Fetch title details including seasons from Net79."""
        url = f"{self.base_url}/api/catalog/title/{media_type}/{tmdb_id}"
        try:
            async with aiohttp.ClientSession(headers=self.default_headers) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.error(f"Error fetching title details for {tmdb_id}: {e}")
        return {}

    async def get_season_episodes(self, tmdb_id: int, season_number: int) -> List[Dict[str, Any]]:
        """Fetch episodes for a specific season from Net79."""
        url = f"{self.base_url}/api/catalog/season/{tmdb_id}/{season_number}"
        try:
            async with aiohttp.ClientSession(headers=self.default_headers) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data.get("episodes", [])
        except Exception as e:
            logger.error(f"Error fetching episodes for season {season_number}: {e}")
        return []

    async def get_download_info(
        self,
        subject_id: str,
        detail_path: str = "",
        season: int = 0,
        episode: int = 0,
        media_type: int = 1
    ) -> Dict[str, Any]:
        """Fetch direct download proxy links and qualities from Net79."""
        u_sid = aiohttp.helpers.quote(str(subject_id), safe="")
        u_dp = aiohttp.helpers.quote(str(detail_path), safe="")
        url = f"{self.base_url}/api/download-info?subjectId={u_sid}&dp={u_dp}&se={season}&ep={episode}&type={media_type}&dubs=1"
        try:
            async with aiohttp.ClientSession(headers=self.default_headers) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        return await resp.json()
        except Exception as e:
            logger.error(f"Error fetching download info: {e}")
        return {}

    async def download_file(
        self,
        proxy_path_or_url: str,
        dest_path: str,
        progress_callback: Optional[Callable[[int, int, float, float], Any]] = None
    ) -> bool:
        """Download file via Net79 proxy with Range headers and live progress."""
        if proxy_path_or_url.startswith("http"):
            full_url = proxy_path_or_url
        else:
            full_url = f"{self.base_url}{proxy_path_or_url}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://net79.cc/",
            "Range": "bytes=0-"
        }

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(full_url, timeout=aiohttp.ClientTimeout(total=3600)) as resp:
                    if resp.status not in (200, 206):
                        logger.error(f"Download failed with HTTP status {resp.status}")
                        return False

                    total_size = int(resp.headers.get("Content-Length", 0))
                    if "Content-Range" in resp.headers:
                        m = re.search(r"/(\d+)", resp.headers["Content-Range"])
                        if m:
                            total_size = int(m.group(1))

                    downloaded = 0
                    start_time = time.time()
                    last_update = 0

                    with open(dest_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(1024 * 512): # 512 KB chunks
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)

                            now = time.time()
                            if progress_callback and (now - last_update >= 3.0 or downloaded == total_size):
                                last_update = now
                                elapsed = now - start_time
                                speed = downloaded / elapsed if elapsed > 0 else 0
                                remaining = total_size - downloaded if total_size > downloaded else 0
                                eta = remaining / speed if speed > 0 else 0
                                try:
                                    res = progress_callback(downloaded, total_size, speed, eta)
                                    if asyncio.iscoroutine(res):
                                        await res
                                except Exception:
                                    pass

            return os.path.exists(dest_path) and os.path.getsize(dest_path) > 0
        except Exception as e:
            logger.error(f"Error downloading from Net79 proxy: {e}", exc_info=True)
            return False

    async def get_metadata(self, url: str) -> Dict[str, Any]:
        clean_url = url.strip().strip("<>\"' ")
        try:
            # Check if watch-tmdb url
            m = re.search(r"watch-tmdb/(\d+)", clean_url)
            if m:
                tmdb_id = int(m.group(1))
                media_type = "tv" if "type=tv" in clean_url else "movie"
                details = await self.get_title_details(tmdb_id, media_type)
                if details:
                    return {
                        "title": details.get("title", "NetMirror Media"),
                        "poster": details.get("poster"),
                        "provider": "Net79 / NetMirror",
                        "ext": "mp4",
                        "size": "Auto",
                        "url": clean_url
                    }

            async with aiohttp.ClientSession(headers=self.default_headers) as session:
                async with session.get(clean_url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=15)) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    title_elem = soup.select_one('h1.title') or soup.select_one('h1') or soup.select_one('title')
                    title = title_elem.text.strip() if title_elem else clean_url.split("/")[-1] or "Net79 Media"
                    poster_elem = soup.select_one('img.poster') or soup.select_one('meta[property="og:image"]')
                    poster = poster_elem.get('src') or poster_elem.get('content') if poster_elem else None

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
        clean_url = url.strip().strip("<>\"' ")
        try:
            # Check if watch-tmdb url
            m = re.search(r"watch-tmdb/(\d+)", clean_url)
            if m:
                tmdb_id = int(m.group(1))
                media_type = 2 if "type=tv" in clean_url else 1
                embed_url = f"{self.base_url}/api/embed-tmdb/{tmdb_id}?type={'tv' if media_type == 2 else 'movie'}&se=1&ep=1"
                async with aiohttp.ClientSession(headers=self.default_headers) as session:
                    async with session.get(embed_url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                        if r.status == 200:
                            data = await r.json()
                            streams = data.get("streams", [])
                            if streams:
                                formats = []
                                for s in streams:
                                    res = s.get("resolution", "720")
                                    formats.append({
                                        "format_id": s.get("url"),
                                        "resolution": f"{res}p",
                                        "note": f"{round(s.get('size', 0) / (1024*1024))}MB",
                                        "url": s.get("url")
                                    })
                                return formats

            return [{"format_id": "best", "resolution": "720p", "note": "Direct Stream", "url": clean_url}]
        except Exception as e:
            logger.error(f"Net79 get_formats error: {e}")
            return [{"format_id": "best", "resolution": "720p", "note": "Default Stream", "url": clean_url}]

    async def get_download_url(self, format_id: str, metadata: Dict[str, Any]) -> str:
        return format_id if format_id != "best" else metadata.get("url", "")
