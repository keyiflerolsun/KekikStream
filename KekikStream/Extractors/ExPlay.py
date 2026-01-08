# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
from urllib.parse import urlparse, parse_qs

class ExPlay(ExtractorBase):
    name     = "ExPlay"
    main_url = "https://explay.store"

    async def extract(self, url, referer=None) -> ExtractResult:
        ext_ref = referer or ""
        
        # URL parsing for partKey
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        part_key = params.get("partKey", [""])[0]
        clean_url = url.split("?partKey=")[0]

        if referer:
            self.httpx.headers.update({"Referer": referer})

        istek = await self.httpx.get(clean_url)
        istek.raise_for_status()

        hp = HTMLHelper(istek.text)

        # videoUrl çıkar
        video_url = hp.regex_first(r'videoUrl":"([^",]+)"')
        if not video_url:
            raise ValueError("videoUrl not found")
        video_url = video_url.replace("\\", "")

        # videoServer çıkar
        video_server = hp.regex_first(r'videoServer":"([^",]+)"')
        if not video_server:
            raise ValueError("videoServer not found")

        # title çıkar
        title = hp.regex_first(r'title":"([^",]+)"')
        title = title.split(".")[-1] if title else "Unknown"
        
        if part_key and "turkce" in part_key.lower():
             title = part_key # Or nicer formatting like SetPlay

        # M3U8 link oluştur
        m3u_link = f"{self.main_url}{video_url}?s={video_server}"

        return ExtractResult(
            name      = f"{self.name} - {title}",
            url       = m3u_link,
            referer   = clean_url, 
            subtitles = []
        )
