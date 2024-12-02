# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
from parsel           import Selector
from base64           import b64decode

class CloseLoadExtractor(ExtractorBase):
    name     = "CloseLoad"
    main_url = "https://closeload.filmmakinesi.de"

    async def extract(self, url, referer=None) -> ExtractResult:
        if referer:
            self.oturum.headers.update({"Referer": referer})

        istek = await self.oturum.get(url)
        istek.raise_for_status()

        secici = Selector(istek.text)
        atob   = secici.re(r"aHR0[0-9a-zA-Z+/=]*")
        if not atob:
            raise ValueError("Base64 kodu bulunamadı.")

        m3u_link = b64decode(f"{atob[0]}===").decode("utf-8")

        await self.close()
        return ExtractResult(
            name      = self.name,
            url       = m3u_link,
            referer   = self.main_url,
            subtitles = []
        )