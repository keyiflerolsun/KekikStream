# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core                           import ExtractorBase, ExtractResult, HTMLHelper
from KekikStream.Core.Extractor.ExtractorModels import Subtitle
import json, re

class VideoParktop(ExtractorBase):
    name     = "VideoParktop"
    main_url = "https://videopark.top"

    supported_domains = ["videopark.top"]

    async def extract(self, url: str, referer: str | None = None) -> list[ExtractResult] | None:
        headers = {"Referer": referer} if referer else None
        resp    = await self.async_cf_get(url, headers=headers)
        secici  = HTMLHelper(resp.text)

        # 1. New Worker Pattern (godrive.erikkalinina1994.workers.dev)
        worker_base = secici.regex_first(r"const\s+WORKER_BASE\s*=\s*['\"]([^'\"]+)['\"]")
        video_id    = secici.regex_first(r"const\s+VIDEO_ID\s*=\s*(\d+)")

        if worker_base and video_id:
            api_base = worker_base.replace("\\", "").rstrip("/")
            info_url = f"{api_base}/v/{video_id}/info"

            try:
                info_resp = await self.async_cf_get(info_url, headers={"Referer": url})
                info_data = info_resp.json()

                results   = []
                qualities = info_data.get("qualities", [])
                if qualities:
                    for q in qualities:
                        results.append(ExtractResult(
                            name    = f"{self.name} | {q}p",
                            url     = f"{api_base}/v/{video_id}?q={q}",
                            referer = url
                        ))
                else:
                    results.append(ExtractResult(
                        name    = self.name,
                        url     = f"{api_base}/v/{video_id}",
                        referer = url
                    ))

                if results:
                    return results
            except Exception:
                pass

        # 2. Old _sd Pattern
        sd_data = secici.regex_first(r'(?s)var\s+_sd\s*=\s*({.*?});')
        if sd_data:
            try:
                data       = json.loads(sd_data)
                stream_url = data.get("stream_url")
                if stream_url:
                    subtitles = []
                    for sub in data.get("subtitles", []):
                        sub_url = sub.get("file")
                        if sub_url:
                            subtitles.append(Subtitle(
                                url  = self.fix_url(sub_url),
                                name = sub.get("label", "Altyazı")
                            ))

                    return [ExtractResult(
                        name      = self.name,
                        url       = self.fix_url(stream_url),
                        referer   = url,
                        subtitles = subtitles
                    )]
            except Exception:
                pass

        # 3. Fallback: Direct file in JWPlayer
        video_url = secici.regex_first(r'file:\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']')
        if video_url:
            return [ExtractResult(name=self.name, url=self.fix_url(video_url), referer=url)]

        return None
