# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from abc                  import ABC, abstractmethod
from httpx                import AsyncClient, Timeout
from cloudscraper         import CloudScraper
from .PluginModels        import MainPageResult, SearchResult, MovieInfo
from ..Media.MediaHandler import MediaHandler
from urllib.parse         import urljoin
import re

class PluginBase(ABC):
    name        = "Plugin"
    language    = "tr"
    main_url    = "https://example.com"
    description = "No description provided."
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    main_page   = {}
    _data       = {}

    def __init__(self):
        self.httpx = AsyncClient(
            headers = {
                "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5)",
                "Accept"     : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            timeout = Timeout(10.0),
        )
        self.media_handler = MediaHandler()
        self.cloudscraper  = CloudScraper()
        self.httpx.headers.update(self.cloudscraper.headers)
        self.httpx.cookies.update(self.cloudscraper.cookies)

    # @abstractmethod
    # async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
    #     """Ana sayfadaki popüler içerikleri döndürür."""
    #     pass

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
        await self.httpx.aclose()

    def fix_url(self, url: str) -> str:
        if not url:
            return ""

        if url.startswith("http") or url.startswith("{\""):
            return url

        return f"https:{url}" if url.startswith("//") else urljoin(self.main_url, url)

    @staticmethod
    def clean_title(title: str) -> str:
        suffixes = [
            " izle", 
            " full film", 
            " filmini full",
            " full türkçe",
            " alt yazılı", 
            " altyazılı", 
            " tr dublaj",
            " hd türkçe",
            " türkçe dublaj",
            " yeşilçam ",
            " erotik fil",
            " türkçe",
            " yerli",
            " tüekçe dublaj",
        ]

        cleaned_title = title.strip()

        for suffix in suffixes:
            cleaned_title = re.sub(f"{re.escape(suffix)}.*$", "", cleaned_title, flags=re.IGNORECASE).strip()

        return cleaned_title