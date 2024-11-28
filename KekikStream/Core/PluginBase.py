# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from abc           import ABC, abstractmethod
from httpx         import AsyncClient, Timeout
from .PluginModels import SearchResult, MovieInfo

class PluginBase(ABC):
    name     = "Plugin"
    main_url = "https://example.com"

    def __init__(self):
        self.oturum = AsyncClient(
            headers = {
                "User-Agent" : "keyiflerolsun/KekikStream",
                "Accept"     : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            timeout = Timeout(10.0),
        )

    @abstractmethod
    async def search(self, query: str) -> list[SearchResult]:
        """Kullanıcı arama sorgusuna göre sonuç döndürür."""
        pass

    @abstractmethod
    async def load_item(self, url: str) -> MovieInfo:
        """Bir medya öğesi hakkında detaylı bilgi döndürür."""
        pass

    @abstractmethod
    async def load_links(self, url: str) -> list[str]:
        """Bir medya öğesi için oynatma bağlantılarını döndürür."""
        pass

    async def close(self):
        await self.oturum.aclose()

    def fix_url(self, partial_url: str):
        if partial_url.startswith("http"):
            return partial_url

        return self.main_url.rstrip("/") + "/" + partial_url.lstrip("/")