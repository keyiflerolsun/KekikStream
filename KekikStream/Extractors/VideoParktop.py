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
        headers = {"Referer": referer} if referer else None
        resp    = await self.async_cf_get(url, headers=headers)
        secici  = HTMLHelper(resp.text)

        # var _sd = {...} formatını yakala
        sd_data = secici.regex_first(r'(?s)var\s+_sd\s*=\s*({.*?});')

        # NEW: WORKER API (videopark.top/vip/ pattern)
        if not sd_data:
            worker_url = secici.regex_first(r"const\s+WORKER_URL\s*=\s*['\"]([^'\"]+)['\"]")
            pub_id     = secici.regex_first(r"const\s+PUB_ID\s*=\s*['\"]([^'\"]+)['\"]")
            video_id   = secici.regex_first(r"const\s+VIDEO_ID\s*=\s*['\"]([^'\"]+)['\"]")

            if worker_url and (pub_id or video_id):
                api_url = f"{worker_url}/api/stream?pubId={pub_id}&title={video_id}&nocache=1"
                if pub_id:
                    api_url = f"{worker_url}/api/stream?pubId={pub_id}&title={video_id}&nocache=1"
                elif video_id:
                    api_url = f"{worker_url}/api/video?id={video_id}&nocache=1"

                try:
                    f_resp = await self.async_cf_get(api_url, headers={"Referer": url})
                    f_data = f_resp.json()

                    stream_url = None
                    if hls := f_data.get("hlsSource"):
                        stream_url = hls.get("file")
                    elif mp4s := f_data.get("mp4Sources"):
                        stream_url = mp4s[0].get("file")

                    if stream_url:
                        return ExtractResult(name=self.name, url=self.fix_url(stream_url), referer=url)
                except Exception:
                    pass

        if not sd_data:
            # Alternatif: playerConfig içindeki source
            stream_url = secici.regex_first(r'(?s)file:\s*(_sd\.stream_url|["\']([^"\']+)["\'])')
            if not stream_url or "_sd" in stream_url:
                 # Iframe fallback
                 iframe_src = secici.select_attr("iframe", "src")
                 if iframe_src:
                     return ExtractResult(name=f"{self.name} (Iframe)", url=self.fix_url(iframe_src), referer=url)

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
