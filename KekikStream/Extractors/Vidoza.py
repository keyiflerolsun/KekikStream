# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper

class Vidoza(ExtractorBase):
    name     = "Vidoza"
    main_url = "https://vidoza.net"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        self.httpx.headers.update({"Referer": referer or url})

        resp = await self.httpx.get(url)
        v_url = HTMLHelper(resp.text).select_attr("source", "src")

        if not v_url:
            raise ValueError(f"Vidoza: Video bulunamadı. {url}")

        return ExtractResult(name=self.name, url=v_url, referer=url)
