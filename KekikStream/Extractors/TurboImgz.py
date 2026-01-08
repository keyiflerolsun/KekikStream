# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper

class TurboImgz(ExtractorBase):
    name     = "TurboImgz"
    main_url = "https://turbo.imgz.me"

    async def extract(self, url, referer=None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        istek = await self.httpx.get(url)
        istek.raise_for_status()

        if video := HTMLHelper(istek.text).regex_first(r'file: "(.*)",'):
            return ExtractResult(
                name      = self.name,
                url       = video,
                referer   = referer or self.main_url,
                subtitles = []
            )
        else:
            raise ValueError("File not found in response.")