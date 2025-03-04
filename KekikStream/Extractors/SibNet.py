# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
import re

class SibNet(ExtractorBase):
    name     = "SibNet"
    main_url = "https://video.sibnet.ru"

    async def extract(self, url, referer=None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        response = await self.httpx.get(url)
        response.raise_for_status()

        match = re.search(r'player\.src\(\[\{src: \"([^\"]+)\"', response.text)
        if not match:
            raise ValueError("m3u bağlantısı bulunamadı.")

        m3u_link = f"{self.main_url}{match[1]}"

        await self.close()
        return ExtractResult(
            name      = self.name,
            url       = m3u_link,
            referer   = url,
            headers   = {},
            subtitles = []
        )