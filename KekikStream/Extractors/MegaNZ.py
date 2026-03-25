# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult


class MegaNZ(ExtractorBase):
    name     = "MegaNZ"
    main_url = "https://mega.nz"

    supported_domains = ["mega.nz", "mega.co.nz"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        # MegaNZ embed linkleri direkt döndürülebilir (bazı player'lar destekler)
        # veya downloader eklentisi tarafından ele alınabilir.
        return ExtractResult(name=self.name, url=url, referer=referer or url)
