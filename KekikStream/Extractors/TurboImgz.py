# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
import re

class TurboImgz(ExtractorBase):
    name     = "TurboImgz"
    main_url = "https://turbo.imgz.me"

    async def extract(self, url, referer=None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        istek = await self.httpx.get(url)
        istek.raise_for_status()

        if video_match := re.search(r'file: "(.*)",', istek.text):
            return ExtractResult(
                name      = self.name,
                url       = video_match[1],
                referer   = referer or self.main_url,
                headers   = {},
                subtitles = []
            )
        else:
            raise ValueError("File not found in response.")