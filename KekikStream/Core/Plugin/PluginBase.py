# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ...CLI                       import konsol
from abc                          import ABC, abstractmethod
from cloudscraper                 import CloudScraper
from httpx                        import AsyncClient
from .PluginModels                import MainPageResult, SearchResult, MovieInfo, SeriesInfo
from ..Media.MediaHandler         import MediaHandler
from ..Extractor.ExtractorManager import ExtractorManager
from ..Extractor.ExtractorModels  import ExtractResult
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

    def __init__(self, proxy: str | dict | None = None):
        # cloudscraper - for bypassing Cloudflare
        self.cloudscraper = CloudScraper()
        if proxy:
            self.cloudscraper.proxies = proxy if isinstance(proxy, dict) else {"http": proxy, "https": proxy}

        # Convert dict proxy to string for httpx if necessary
        httpx_proxy = proxy
        if isinstance(proxy, dict):
            httpx_proxy = proxy.get("https") or proxy.get("http")

        # httpx - lightweight and safe for most HTTP requests
        self.httpx = AsyncClient(
            timeout          = 3,
            follow_redirects = True,
            proxy            = httpx_proxy
        )
        self.httpx.headers.update(self.cloudscraper.headers)
        self.httpx.cookies.update(self.cloudscraper.cookies)
        self.httpx.headers.update({
            "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 15.7; rv:135.0) Gecko/20100101 Firefox/135.0",
            "Accept"     : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })

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
    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        """Bir medya öğesi hakkında detaylı bilgi döndürür."""
        pass

    @abstractmethod
    async def load_links(self, url: str) -> list[ExtractResult]:
        """
        Bir medya öğesi için oynatma bağlantılarını döndürür.

        Args:
            url: Medya URL'si

        Returns:
            ExtractResult listesi, her biri şu alanları içerir:
            - url (str, zorunlu): Video URL'si
            - name (str, zorunlu): Gösterim adı (tüm bilgileri içerir)
            - referer (str, opsiyonel): Referer header
            - subtitles (list[Subtitle], opsiyonel): Altyazı listesi

        Example:
            [
                ExtractResult(
                    url="https://example.com/video.m3u8",
                    name="HDFilmCehennemi | 1080p TR Dublaj"
                )
            ]
        """
        pass

    async def close(self):
        """Close HTTP client."""
        await self.httpx.aclose()

    def fix_url(self, url: str) -> str:
        if not url:
            return ""

        if url.startswith("http") or url.startswith("{\""):
            return url

        return f"https:{url}" if url.startswith("//") else urljoin(self.main_url, url)

    async def extract(self, url: str, referer: str = None, prefix: str | None = None) -> ExtractResult | None:
        """
        Extractor ile video URL'sini çıkarır.

        Args:
            url: Iframe veya video URL'si
            referer: Referer header (varsayılan: plugin main_url)
            prefix: İsmin başına eklenecek opsiyonel etiket (örn: "Türkçe Dublaj")

        Returns:
            ExtractResult: Extractor sonucu (name prefix ile birleştirilmiş) veya None

        Extractor bulunamadığında veya hata oluştuğunda uyarı verir.
        """
        if referer is None:
            referer = f"{self.main_url}/"

        extractor = self.ex_manager.find_extractor(url)
        if not extractor:
            konsol.log(f"[magenta][?] {self.name} » Extractor bulunamadı: {url}")
            return None

        try:
            data = await extractor.extract(url, referer=referer)

            # Liste ise her bir öğe için prefix ekle
            if isinstance(data, list):
                for item in data:
                    if prefix and item.name:
                        item.name = f"{prefix} | {item.name}"
                return data

            # Tekil öğe ise
            if prefix and data.name:
                data.name = f"{prefix} | {data.name}"

            return data
        except Exception as hata:
            konsol.log(f"[red][!] {self.name} » Extractor hatası ({extractor.name}): {hata}")
            return None

    @staticmethod
    def clean_title(title: str | None) -> str | None:
        if not title:
            return None

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

    async def play(self, **kwargs):
        """
        Varsayılan oynatma metodu.
        Tüm pluginlerde ortak kullanılır.
        """
        extract_result = ExtractResult(**kwargs)
        self.media_handler.title = kwargs.get("name")
        if self.name not in self.media_handler.title:
            self.media_handler.title = f"{self.name} | {self.media_handler.title}"

        self.media_handler.play_media(extract_result)