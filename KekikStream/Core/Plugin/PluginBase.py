# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from abc                          import ABC, abstractmethod
from httpx                        import AsyncClient, Timeout
from cloudscraper                 import CloudScraper
from .PluginModels                import MainPageResult, SearchResult, MovieInfo
from ..Media.MediaHandler         import MediaHandler
from ..Extractor.ExtractorManager import ExtractorManager
from urllib.parse                 import urljoin
import re

class PluginBase(ABC):
    name        = "Plugin"
    language    = "tr"
    main_url    = "https://example.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "No description provided."

    main_page   = {}

    async def url_update(self, new_url: str):
        self.favicon   = self.favicon.replace(self.main_url, new_url)
        self.main_page = {url.replace(self.main_url, new_url): category for url, category in self.main_page.items()}
        self.main_url  = new_url

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
        self.ex_manager    = ExtractorManager()
        self.httpx.headers.update(self.cloudscraper.headers)
        self.httpx.headers.update({"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.3"})
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
    async def load_links(self, url: str) -> list[dict]:
        """
        Bir medya öğesi için oynatma bağlantılarını döndürür.
        
        Args:
            url: Medya URL'si
            
        Returns:
            Dictionary listesi, her biri şu alanları içerir:
            - url (str, zorunlu): Video URL'si
            - name (str, zorunlu): Gösterim adı (tüm bilgileri içerir)
            - referer (str, opsiyonel): Referer header
            - subtitles (list, opsiyonel): Altyazı listesi
        
        Example:
            [
                {
                    "url": "https://example.com/video.m3u8",
                    "name": "HDFilmCehennemi | 1080p TR Dublaj"
                }
            ]
        """
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