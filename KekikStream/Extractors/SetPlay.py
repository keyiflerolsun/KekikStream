# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper
from urllib.parse import urlparse, parse_qs

class SetPlay(ExtractorBase):
    name     = "SetPlay"
    main_url = "https://setplay.shop"

    supported_domains = ["setplay.cfd", "setplay.shop", "setplay.site"]

    def can_handle_url(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        self.httpx.headers.update({"Referer": referer or url})
        base_url = self.get_base_url(url)

        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)

        v_url = sel.regex_first(r'videoUrl":"([^",]+)"')
        v_srv = sel.regex_first(r'videoServer":"([^",]+)"')
        if not v_url or not v_srv:
            raise ValueError(f"SetPlay: Video url/server bulunamadı. {url}")

        params   = parse_qs(urlparse(url).query)
        part_key = params.get("partKey", [""])[0].lower()
        
        suffix = "Bilinmiyor"
        if "turkcedublaj" in part_key: suffix = "Dublaj"
        elif "turkcealtyazi" in part_key: suffix = "Altyazı"
        else:
            title = sel.regex_first(r'title":"([^",]+)"')
            if title: suffix = title.split(".")[-1]

        return ExtractResult(
            name      = f"{self.name} - {suffix}",
            url       = f"{base_url}{v_url.replace('\\', '')}?s={v_srv}",
            referer   = url
        )
