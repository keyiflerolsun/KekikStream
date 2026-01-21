# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper

class Vidoza(ExtractorBase):
    name     = "Vidoza"
    main_url = "https://vidoza.net"

    async def extract(self, url: str, referer: str = None) -> ExtractResult | None:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        istek  = await self.httpx.get(url)
        helper = HTMLHelper(istek.text)
        
        video_url = helper.select_attr("source", "src")
        
        if video_url:
            return ExtractResult(
                name    = self.name,
                url     = video_url,
                referer = url
            )
            
        return None
