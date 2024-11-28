# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from abc              import ABC, abstractmethod
from typing           import Optional
from .ExtractorModels import ExtractResult

class ExtractorBase(ABC):
    name     = "Extractor"
    main_url = ""

    def can_handle_url(self, url: str) -> bool:
        """URL'nin bu extractor tarafından işlenip işlenemeyeceğini kontrol eder."""
        return self.main_url in url

    @abstractmethod
    async def extract(self, url: str, referer: Optional[str] = None) -> ExtractResult:
        """Bir URL'den medya bilgilerini çıkarır."""
        pass