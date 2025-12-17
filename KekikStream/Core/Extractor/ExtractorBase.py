# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from abc              import ABC, abstractmethod
from curl_cffi        import AsyncSession
from cloudscraper     import CloudScraper
from httpx            import AsyncClient
from typing           import Optional
from .ExtractorModels import ExtractResult
from urllib.parse     import urljoin

class ExtractorBase(ABC):
    # Çıkarıcının temel özellikleri
    name     = "Extractor"
    main_url = ""
    requires_cffi = False

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

    def can_handle_url(self, url: str) -> bool:
        # URL'nin bu çıkarıcı tarafından işlenip işlenemeyeceğini kontrol et
        return self.main_url in url

    @abstractmethod
    async def extract(self, url: str, referer: Optional[str] = None) -> ExtractResult:
        # Alt sınıflar tarafından uygulanacak medya çıkarma fonksiyonu
        pass

    async def close(self):
        """Close both HTTP clients if they exist."""
        await self.httpx.aclose()
        if self.cffi:
            await self.cffi.close()

    def fix_url(self, url: str) -> str:
        # Eksik URL'leri düzelt ve tam URL formatına çevir
        if not url:
            return ""

        if url.startswith("http") or url.startswith("{\""):
            return url

        return f"https:{url}" if url.startswith("//") else urljoin(self.main_url, url)