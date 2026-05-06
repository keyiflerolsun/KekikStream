# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core                           import ExtractorBase, ExtractResult, HTMLHelper
from KekikStream.Core.Extractor.ExtractorModels import Subtitle
from urllib.parse                               import urlparse, parse_qs
import json

class VideoParktop(ExtractorBase):
    name     = "VideoParktop"
    main_url = "https://videopark.top"

    supported_domains = ["videopark.top"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        resp   = await self.async_cf_get(url, headers={"Referer": referer or self.main_url})
        secici = HTMLHelper(resp.text)

        # var _sd = {...} formatını yakala
        sd_data = secici.regex_first(r'var\s+_sd\s*=\s*({.*?});', resp.text)
        if not sd_data:
            # Alternatif: playerConfig içindeki source
            stream_url = secici.regex_first(r'file:\s*(_sd\.stream_url|["\']([^"\']+)["\'])')
            if not stream_url or "_sd" in stream_url:
                 raise ValueError(f"VideoParktop: stream_url bulunamadı. {url}")
            return ExtractResult(name=self.name, url=self.fix_url(stream_url), referer=url)

        try:
            data       = json.loads(sd_data)
            stream_url = data.get("stream_url")
            if not stream_url:
                raise ValueError("stream_url not in _sd")

            subtitles = []
            for sub in data.get("subtitles", []):
                subtitles.append(Subtitle(
                    url  = self.fix_url(sub.get("file")),
                    name = sub.get("label", "Altyazı")
                ))

            return ExtractResult(
                name      = self.name,
                url       = self.fix_url(stream_url),
                referer   = url,
                subtitles = subtitles
            )
        except Exception as e:
             raise ValueError(f"VideoParktop: JSON decode hatası: {e}. {url}")
