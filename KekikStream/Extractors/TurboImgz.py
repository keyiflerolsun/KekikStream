# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper

class TurboImgz(ExtractorBase):
    name     = "TurboImgz"
    main_url = "https://turbo.imgz.me"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        self.httpx.headers.update({"Referer": referer or url})

        resp = await self.httpx.get(url)
        v_url = HTMLHelper(resp.text).regex_first(r'file: "(.*)",')
        if not v_url:
            raise ValueError(f"TurboImgz: Video bulunamadı. {url}")

        return ExtractResult(name=self.name, url=v_url, referer=referer or self.main_url)
