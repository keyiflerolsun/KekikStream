# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from abc              import ABC, abstractmethod
from cloudscraper     import CloudScraper
from httpx            import AsyncClient
from typing           import Optional
from .ExtractorModels import ExtractResult
from urllib.parse     import urljoin, urlparse

class ExtractorBase(ABC):
    # Çıkarıcının temel özellikleri
    name     = "Extractor"
    main_url = ""

    def __init__(self):
        # cloudscraper - for bypassing Cloudflare
        self.cloudscraper = CloudScraper()

        # httpx - lightweight and safe for most HTTP requests
        self.httpx = AsyncClient(timeout = 10)
        self.httpx.headers.update(self.cloudscraper.headers)
        self.httpx.cookies.update(self.cloudscraper.cookies)
        self.httpx.headers.update({
            "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 15.7; rv:135.0) Gecko/20100101 Firefox/135.0",
            "Accept"     : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })

    def can_handle_url(self, url: str) -> bool:
        # URL'nin bu çıkarıcı tarafından işlenip işlenemeyeceğini kontrol et
        return self.main_url in url

    def get_base_url(self, url: str) -> str:
        """URL'den base URL'i çıkar (scheme + netloc)"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    @abstractmethod
    async def extract(self, url: str, referer: Optional[str] = None) -> ExtractResult:
        # Alt sınıflar tarafından uygulanacak medya çıkarma fonksiyonu
        pass

    async def close(self):
        """Close HTTP client."""
        await self.httpx.aclose()

    def fix_url(self, url: str) -> str:
        # Eksik URL'leri düzelt ve tam URL formatına çevir
        if not url:
            return ""

        if url.startswith("http") or url.startswith("{\""):
            return url.replace("\\", "")

        url = f"https:{url}" if url.startswith("//") else urljoin(self.main_url, url)
        return url.replace("\\", "")
