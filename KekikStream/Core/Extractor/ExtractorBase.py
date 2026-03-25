# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from abc                import ABC, abstractmethod
from curl_cffi.requests import AsyncSession
from httpx              import AsyncClient
from typing             import Optional
from .ExtractorModels   import ExtractResult
from urllib.parse       import urljoin, urlparse

class ExtractorBase(ABC):
    # Çıkarıcının temel özellikleri
    name     = "Extractor"
    main_url = ""

    def __init__(self):
        # curl_cffi - for bypassing Cloudflare TLS/HTTP2 fingerprints
        self._cf_session = AsyncSession(impersonate="chrome")
        self._cf_session.headers.update({
            "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 15.7; rv:135.0) Gecko/20100101 Firefox/135.0",
            "Accept"     : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })

        # httpx - lightweight and safe for most HTTP requests
        self.httpx = AsyncClient(timeout = 10)
        self.httpx.headers.update(self._cf_session.headers)
        self.httpx.headers.update({
            "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 15.7; rv:135.0) Gecko/20100101 Firefox/135.0",
            "Accept"     : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })

    def can_handle_url(self, url: str) -> bool:
        # URL'nin bu çıkarıcı tarafından işlenip işlenemeyeceğini kontrol et
        if self.main_url and self.main_url in url:
            return True

        if hasattr(self, "supported_domains"):
            for domain in self.supported_domains:
                if domain in url:
                    return True

        return False

    def get_base_url(self, url: str) -> str:
        """URL'den base URL'i çıkar (scheme + netloc)"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    @abstractmethod
    async def extract(self, url: str, referer: Optional[str] = None) -> ExtractResult:
        # Alt sınıflar tarafından uygulanacak medya çıkarma fonksiyonu
        pass

    async def close(self):
        """Close HTTP clients."""
        await self.httpx.aclose()
        await self._cf_session.close()

    async def async_cf_get(self, url: str, **kwargs):
        """curl_cffi.AsyncSession ile Cloudflare bypasslı GET isteği."""
        return await self._cf_session.get(url, **kwargs)

    async def async_cf_post(self, url: str, **kwargs):
        """curl_cffi.AsyncSession ile Cloudflare bypasslı POST isteği."""
        return await self._cf_session.post(url, **kwargs)

    def fix_url(self, url: str) -> str:
        # Eksik URL'leri düzelt ve tam URL formatına çevir
        if not url:
            return ""

        if url.startswith("http") or url.startswith("{\""):
            return url.replace("\\", "")

        url = f"https:{url}" if url.startswith("//") else urljoin(self.main_url, url)
        return url.replace("\\", "")
