# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper
import json, re

class ErikWorker(ExtractorBase):
    name     = "ErikWorker"
    main_url = "https://erikkalinina1994.workers.dev"

    async def extract(self, url: str, referer: str | None = None) -> list[ExtractResult] | None:
        headers = {"Referer": referer or self.main_url}
        resp    = await self.async_cf_get(url, headers=headers)
        secici  = HTMLHelper(resp.text)

        # /play/ pattern
        if "/play/" in url:
            # Check for qualities in JS
            match = re.search(r"const\s+qualities\s*=\s*(\[.*?\])", resp.text)
            if match:
                try:
                    qualities = json.loads(match.group(1))
                    results   = []
                    # Usually qualities are like [360, 720, 1080]
                    # The file URL is usually the same page but without /play/ or with ?q=
                    # Let's check the JS more closely
                    api_base = url.split("/play/")[0]
                    token    = url.split("/play/")[1]

                    for q in qualities:
                         results.append(ExtractResult(
                             name    = f"{self.name} | {q}p",
                             url     = f"{api_base}/v/{token}?q={q}",
                             referer = url
                         ))
                    return results
                except Exception:
                    pass

        # Fallback: Check for JWPlayer sources
        video_url = secici.regex_first(r'file:\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']')
        if video_url:
            return [ExtractResult(name=self.name, url=self.fix_url(video_url), referer=url)]

        return None
