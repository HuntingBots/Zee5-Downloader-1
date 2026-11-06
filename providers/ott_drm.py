from typing import List, Dict, Any
from .base import BaseProvider

class OTTDRMProvider(BaseProvider):
    DOMAINS = {
        "sonyliv.com": "SonyLIV",
        "zee5.com": "Zee5",
        "hotstar.com": "Disney+ Hotstar",
        "jiocinema.com": "JioCinema",
        "netflix.com": "Netflix",
        "primevideo.com": "Amazon Prime Video"
    }

    async def can_handle(self, url: str) -> bool:
        u = url.strip().strip("<>\"' ").lower()
        return any(d in u for d in self.DOMAINS)

    def get_platform_name(self, url: str) -> str:
        u = url.lower()
        for d, name in self.DOMAINS.items():
            if d in u:
                return name
        return "OTT Platform"

    async def get_metadata(self, url: str) -> Dict[str, Any]:
        platform = self.get_platform_name(url)
        return {
            "title": f"{platform} Protected Content",
            "provider": platform,
            "ext": "mp4",
            "size": "DRM Protected",
            "is_drm": True,
            "url": url
        }

    async def get_formats(self, url: str) -> List[Dict[str, Any]]:
        return []

    async def get_download_url(self, format_id: str, metadata: Dict[str, Any]) -> str:
        return ""
