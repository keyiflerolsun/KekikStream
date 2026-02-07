# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper

class SibNet(ExtractorBase):
    name     = "SibNet"
    main_url = "https://video.sibnet.ru"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        self.httpx.headers.update({"Referer": referer or url})

        resp = await self.httpx.get(url)
        path = HTMLHelper(resp.text).regex_first(r'player\.src\(\[\{src: "([^\"]+)"')
        if not path:
            raise ValueError(f"SibNet: Video yolu bulunamadı. {url}")

        return ExtractResult(name=self.name, url=f"{self.main_url}{path}", referer=url)
