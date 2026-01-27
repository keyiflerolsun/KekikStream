# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper

class Abstream(ExtractorBase):
    name     = "Abstream"
    main_url = "https://abstream.to"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        istek  = await self.httpx.get(
            url     = url,
            headers = {
                "Accept-Language" : "en-US,en;q=0.5",
                "Referer"         : referer or self.main_url,
            }
        )
        secici    = HTMLHelper(istek.text)
        video_url = secici.regex_first(r'file:"([^"]*)"')

        if not video_url:
            raise ValueError(f"Abstream: Video URL bulunamadı. {url}")

        return ExtractResult(
            name    = self.name,
            url     = video_url,
            referer = referer or self.main_url
        )
