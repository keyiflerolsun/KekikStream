# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
from urllib.parse import urlparse, parse_qs
import re

class SetPlay(ExtractorBase):
    name     = "SetPlay"
    main_url = "https://setplay.shop"

    # Birden fazla domain destekle
    supported_domains = ["setplay.cfd", "setplay.shop", "setplay.site"]

    def can_handle_url(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)

    async def extract(self, url, referer=None) -> ExtractResult:
        ext_ref = referer or ""

        if referer:
            self.httpx.headers.update({"Referer": referer})

        # Dinamik base URL kullan
        base_url = self.get_base_url(url)

        istek = await self.httpx.get(url)
        istek.raise_for_status()

        # videoUrl çıkar
        video_url_match = re.search(r'videoUrl":"([^",]+)"', istek.text)
        if not video_url_match:
            raise ValueError("videoUrl not found")
        video_url = video_url_match[1].replace("\\", "")

        # videoServer çıkar
        video_server_match = re.search(r'videoServer":"([^",]+)"', istek.text)
        if not video_server_match:
            raise ValueError("videoServer not found")
        video_server = video_server_match[1]

        # title çıkar (opsiyonel)
        title_match = re.search(r'title":"([^",]+)"', istek.text)
        title_base = title_match[1].split(".")[-1] if title_match else "Unknown"
        
        # partKey logic
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        part_key = params.get("partKey", [""])[0]
        
        name_suffix = ""
        if "turkcedublaj" in part_key.lower():
            name_suffix = "Dublaj"
        elif "turkcealtyazi" in part_key.lower():
            name_suffix = "Altyazı"
        else:
            name_suffix = title_base

        # M3U8 link oluştur - base_url kullan (main_url yerine)
        m3u_link = f"{base_url}{video_url}?s={video_server}"

        return ExtractResult(
            name      = f"{self.name} - {name_suffix}",
            url       = m3u_link,
            referer   = url,
            subtitles = []
        )
