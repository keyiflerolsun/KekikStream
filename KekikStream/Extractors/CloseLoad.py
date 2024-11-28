# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
from parsel           import Selector
from httpx            import AsyncClient
from base64           import b64decode

class CloseLoadExtractor(ExtractorBase):
    name     = "CloseLoad"
    main_url = "https://closeload.filmmakinesi.de"

    async def extract(self, url, referer=None) -> ExtractResult:
        """Bir URL'den medya bilgilerini çıkarır."""
        async with AsyncClient() as client:
            response = await client.get(url, headers={"Referer": referer} if referer else {})
            response.raise_for_status()

        selector = Selector(response.text)
        atob     = selector.re(r"aHR0[0-9a-zA-Z+/=]*")
        if not atob:
            raise ValueError("Base64 kodu bulunamadı.")

        m3u_link = b64decode(f"{atob[0]}===").decode("utf-8")

        return ExtractResult(
            name      = self.name,
            url       = m3u_link,
            referer   = self.main_url,
            subtitles = []
        )