from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseProvider(ABC):
    @abstractmethod
    async def can_handle(self, url: str) -> bool:
        """Check if this provider can handle the given URL."""
        pass

    @abstractmethod
    async def get_metadata(self, url: str) -> Dict[str, Any]:
        """Retrieve metadata for the content."""
        pass

    @abstractmethod
    async def get_formats(self, url: str) -> List[Dict[str, Any]]:
        """Retrieve available media formats."""
        pass

    @abstractmethod
    async def get_download_url(self, format_id: str, metadata: Dict[str, Any]) -> str:
        """Get the actual download URL for a specific format."""
        pass
