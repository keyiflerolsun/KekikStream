# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from abc                import ABC, abstractmethod
from curl_cffi.requests import AsyncSession
from httpx              import AsyncClient
from .ExtractorModels   import ExtractResult
from urllib.parse       import urlparse
from ..Helpers          import PlayabilityHelper, fix_url
import asyncio

class ExtractorBase(ABC):
    # Çıkarıcının temel özellikleri
    name     : str = "Extractor"
    main_url : str = ""

    def __init__(self):
        # curl_cffi - for bypassing Cloudflare TLS/HTTP2 fingerprints
        self._cf_session = AsyncSession(impersonate="firefox")
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

        # Metot sarmalama (ExtractResult URL'lerinin oynatılabilirliğini doğrular)
        self._wrap_extract_method()

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
    async def extract(self, url: str, referer: str | None = None) -> ExtractResult | list[ExtractResult] | None:
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
        return fix_url(url, self.main_url)

    def _wrap_extract_method(self):
        """extract metodunu dinamik olarak sarmalar ve oynatılamayan linkleri ayıklar."""
        original_extract = getattr(self, "extract", None)
        if not original_extract or getattr(original_extract, "__wb_wrapped_extract__", False):
            return

        async def wrapped_extract(url: str, referer: str | None = None, *args, **kwargs) -> ExtractResult | list[ExtractResult] | None:
            try:
                res = await original_extract(url, referer, *args, **kwargs)
                if not res:
                    return None

                # Liste ise asyncio.gather ile paralel doğrulama yap
                if isinstance(res, list):
                    extract_items = [item for item in res if isinstance(item, ExtractResult)]

                    if not extract_items:
                        return None

                    # Görevleri hazırla
                    tasks = [PlayabilityHelper.is_url_playable(item) for item in extract_items]

                    # Paralel olarak çalıştır
                    playability_results = await asyncio.gather(*tasks)

                    # Sonuçları eşleştir ve filtrele
                    valid_results = [
                        item for item, (is_playable, _) in zip(extract_items, playability_results)
                        if is_playable
                    ]

                    return valid_results if valid_results else None

                # Tekil öğe ise tekli doğrulama yap
                elif isinstance(res, ExtractResult):
                    is_playable, _ = await PlayabilityHelper.is_url_playable(res)
                    if is_playable:
                        return res
                    else:
                        return None

                return res
            except Exception as e:
                raise e

        wrapped_extract.__wb_wrapped_extract__ = True
        self.extract                           = wrapped_extract
