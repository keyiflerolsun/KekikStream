# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
import re

class EksenLoad(ExtractorBase):
    name     = "EksenLoad"
    main_url = "https://eksenload.top"

    def can_handle_url(self, url: str) -> bool:
        return "eksenload" in url

    async def extract(self, url: str, referer: str | None = None) -> list[ExtractResult] | None:
        headers = {"Referer": referer or self.main_url}
        resp    = await self.async_cf_get(url, headers=headers)
        html    = resp.text

        # JWPlayer file pattern
        files = re.findall(r'file:\s*["\']([^"\']+)["\']', html)
        if not files:
            return None

        video_url = None
        subtitles = []

        for f in files:
            full_f = self.fix_url(f)
            if ".m3u8" in full_f or ".mp4" in full_f:
                video_url = full_f
            elif ".vtt" in full_f or ".srt" in full_f:
                name = "Türkçe" if "_tur" in full_f.lower() else ("İngilizce" if "_eng" in full_f.lower() else "Altyazı")
                subtitles.append(Subtitle(name=name, url=full_f))

        if not video_url:
            return None

        return [ExtractResult(
            name      = self.name,
            url       = video_url,
            referer   = url,
            subtitles = subtitles
        )]
