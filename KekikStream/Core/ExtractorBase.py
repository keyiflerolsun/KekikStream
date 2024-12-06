# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from abc              import ABC, abstractmethod
from httpx            import AsyncClient, Timeout
from cloudscraper     import CloudScraper
from typing           import Optional
from .ExtractorModels import ExtractResult

class ExtractorBase(ABC):
    name     = "Extractor"
    main_url = ""

    def __init__(self):
        self.oturum = AsyncClient(
            headers = {
                "User-Agent" : "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5)",
                "Accept"     : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            timeout = Timeout(10.0)
        )
        self.cloudscraper  = CloudScraper()

    def can_handle_url(self, url: str) -> bool:
        """URL'nin bu extractor tarafından işlenip işlenemeyeceğini kontrol eder."""
        return self.main_url in url

    @abstractmethod
    async def extract(self, url: str, referer: Optional[str] = None) -> ExtractResult:
        """Bir URL'den medya bilgilerini çıkarır."""
        pass

    async def close(self):
        await self.oturum.aclose()

    def fix_url(self, url: str) -> str:
        if not url:
            return ""

        if url.startswith("http") or url.startswith("{\""):
            return url

        return f"https:{url}" if url.startswith("//") else urljoin(self.main_url, url)