# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
import re, json

class TRPlayer(ExtractorBase):
    name              = "TRPlayer"
    main_url          = "https://watch.trplayer.com"
    supported_domains = ["watch.trplayer.com", "trplayer.com"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        # Standardize User-Agent and Referer headers
        self.httpx.headers.update({
            "Referer" : referer or "https://filmcenneti.org/",
            "Origin"  : referer or "https://filmcenneti.org",
        })

        resp   = await self.httpx.get(url)
        html   = resp.text
        origin = f"{resp.url.scheme}://{resp.url.host}"

        # 1. Parse 'var video = { ... };' JSON structure
        video_match = re.search(r'var video\s*=\s*(\{.*?\});', html)
        if not video_match:
            # Fallback to direct sources parsing
            file_match = re.search(r'sources:\s*\[\{\s*file:\s*"([^"]+)"', html)
            if not file_match:
                raise ValueError(f"TRPlayer: Source not found. {url}")

            video_url = file_match.group(1)
            if not video_url.startswith("http"):
                video_url = f"{origin}/{video_url.lstrip('/')}"

            return ExtractResult(
                name    = self.name,
                url     = video_url,
                referer = url,
            )

        try:
            video_data = json.loads(video_match.group(1))
            uid        = video_data.get("uid")
            md5        = video_data.get("md5")
            v_id       = video_data.get("id")
            status     = video_data.get("status", "1")

            if not uid or not md5 or not v_id:
                raise ValueError("Incomplete video JSON data")

            # Format: /m3u8/{uid}/{md5}/master.txt?s=1&id={id}&cache={status}
            video_url = f"{origin}/m3u8/{uid}/{md5}/master.txt?s=1&id={v_id}&cache={status}"

            # Handle subtitles if present
            subtitles = []
            raw_subs  = video_data.get("subtitles")
            if raw_subs:
                if isinstance(raw_subs, str):
                    try:
                        raw_subs = json.loads(raw_subs)
                    except Exception:
                        pass

                if isinstance(raw_subs, list):
                    for sub in raw_subs:
                        s_url   = sub.get("file")
                        s_label = sub.get("label") or "Turkish"
                        if s_url:
                            if not s_url.startswith("http"):
                                s_url = f"{origin}/{s_url.lstrip('/')}"
                            subtitles.append(Subtitle(name=s_label, url=s_url))

        except Exception as e:
            # Fallback if JSON parsing fails
            file_match = re.search(r'sources:\s*\[\{\s*file:\s*"([^"]+)"', html)
            if not file_match:
                raise ValueError(f"TRPlayer: Parsing failed and fallback not found. Error: {e}")

            video_url = file_match.group(1)
            if not video_url.startswith("http"):
                video_url = f"{origin}/{video_url.lstrip('/')}"
            subtitles = []

        return ExtractResult(
            name      = self.name,
            url       = video_url,
            referer   = url,
            subtitles = subtitles,
        )
