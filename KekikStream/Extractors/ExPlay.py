# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper
from urllib.parse     import urlparse, parse_qs

class ExPlay(ExtractorBase):
    name     = "ExPlay"
    main_url = "https://explay.store"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        self.httpx.headers.update({"Referer": referer or url})
        
        # Clean URL from partKey for initial request
        clean_url = url.split("?")[0]
        resp = await self.httpx.get(clean_url)
        sel  = HTMLHelper(resp.text)

        v_url = sel.regex_first(r'videoUrl":"([^",]+)"')
        v_srv = sel.regex_first(r'videoServer":"([^",]+)"')
        if not v_url or not v_srv:
            raise ValueError(f"ExPlay: Video url/server bulunamadı. {url}")

        params   = parse_qs(urlparse(url).query)
        part_key = params.get("partKey", [""])[0]
        
        suffix = part_key or "Bilinmiyor"
        if not part_key:
            title = sel.regex_first(r'title":"([^",]+)"')
            if title:
                suffix = title.split(".")[-1]

        return ExtractResult(
            name    = f"{self.name} - {suffix}",
            url     = f"{self.main_url}{v_url.replace('\\', '')}?s={v_srv}",
            referer = clean_url
        )
