# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
import re

class JFVid(ExtractorBase):
    name     = "JFVid"
    main_url = "https://jfvid.com"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        # /play/ endpoint'inden encodedId'yi al
        # URL format: https://xxx.jfvid.com/play/{encodedId}
        if "/play/" in url:
            encoded_id = url.split("/play/")[-1]
            stream_url = f"{self.main_url}/stream/{encoded_id}"
        elif "/stream/" in url:
            # Zaten stream URL ise doğrudan kullan
            stream_url = url
        else:
            raise ValueError(f"JFVid: Desteklenmeyen URL formatı. {url}")

        # Stream endpoint'i direkt m3u8 master playlist döndürür
        return ExtractResult(
            name      = self.name,
            url       = stream_url,
            referer   = referer,
            subtitles = []
        )
