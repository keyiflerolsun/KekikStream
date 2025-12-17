# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from abc                          import ABC, abstractmethod
from curl_cffi                    import AsyncSession
from cloudscraper                 import CloudScraper
from httpx                        import AsyncClient
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

    requires_cffi = False

    main_page   = {}

    async def url_update(self, new_url: str):
        self.favicon   = self.favicon.replace(self.main_url, new_url)
        self.main_page = {url.replace(self.main_url, new_url): category for url, category in self.main_page.items()}
        self.main_url  = new_url

    def __init__(self):
        # cloudscraper - for bypassing Cloudflare
        self.cloudscraper = CloudScraper()

        # httpx - lightweight and safe for most HTTP requests
        self.httpx = AsyncClient(
            timeout          = 3,
            follow_redirects = True,
        )
        self.httpx.headers.update(self.cloudscraper.headers)
        self.httpx.cookies.update(self.cloudscraper.cookies)

        # curl_cffi - only initialize if needed for anti-bot bypass
        self.cffi = None

        if self.requires_cffi:
            self.cffi = AsyncSession(impersonate="firefox135")
            self.cffi.cookies.update(self.cloudscraper.cookies)
            self.cffi.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 15.7; rv:135.0) Gecko/20100101 Firefox/135.0"})

        self.media_handler = MediaHandler()
        self.ex_manager    = ExtractorManager()

    @abstractmethod
    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        """Ana sayfadaki popüler içerikleri döndürür."""
        pass

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
        """Close both HTTP clients if they exist."""
        await self.httpx.aclose()
        if self.cffi:
            await self.cffi.close()

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