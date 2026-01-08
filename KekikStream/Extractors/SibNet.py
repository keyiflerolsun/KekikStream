# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper

class SibNet(ExtractorBase):
    name     = "SibNet"
    main_url = "https://video.sibnet.ru"

    async def extract(self, url, referer=None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        response = await self.httpx.get(url)
        response.raise_for_status()

        m3u_suffix = HTMLHelper(response.text).regex_first(r'player\.src\(\[\{src: "([^\"]+)"')
        if not m3u_suffix:
            raise ValueError("m3u bağlantısı bulunamadı.")

        m3u_link = f"{self.main_url}{m3u_suffix}"

        return ExtractResult(
            name      = self.name,
            url       = m3u_link,
            referer   = url,
            subtitles = []
        )