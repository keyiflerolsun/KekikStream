# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult


class MegaNZ(ExtractorBase):
    name     = "MegaNZ"
    main_url = "https://mega.nz"

    supported_domains = ["mega.nz", "mega.co.nz"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        raise ValueError(f"MegaNZ: Doğrudan medya URL'si alınamıyor, sadece web player embed'i mevcut. {url}")
