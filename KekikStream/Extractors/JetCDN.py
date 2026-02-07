# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
import json, re

class JetCDN(ExtractorBase):
    name     = "JetCDN"
    main_url = "https://jetcdn.org"

    async def extract(self, url: str, referer: str = None) -> list[ExtractResult]:
        resp = await self.httpx.get(url)
        content = resp.text

        results = []

        # Extract URLs directly via regex since the JS object might not be strict JSON
        video_original = re.search(r'videoUrlOriginal:\s*"([^"]+)"', content)
        video_turkish  = re.search(r'videoUrlTurkish:\s*"([^"]+)"', content)

        # Subtitles (Safe extraction)
        subtitles = []
        sub_match = re.search(r'subtitles:\s*(\[.*?\]),', content, re.DOTALL)
        if sub_match:
            try:
                # Clean up JS list to be more JSON-like (quotes for keys)
                json_str = re.sub(r'(\w+):', r'"\1":', sub_match.group(1))
                subs_data = json.loads(json_str)
                for sub in subs_data:
                    if s_url := sub.get("file"):
                        subtitles.append(Subtitle(name=sub.get("label", "Unknown"), url=s_url.replace("\\", "")))
            except:
                pass

        if video_turkish:
            results.append(ExtractResult(
                name      = f"{self.name} (TR Dublaj)",
                url       = video_turkish.group(1).replace("\\", ""),
                referer   = url,
                subtitles = subtitles
            ))

        if video_original:
            results.append(ExtractResult(
                name      = f"{self.name} (Orijinal)",
                url       = video_original.group(1).replace("\\", ""),
                referer   = url,
                subtitles = subtitles
            ))

        return results
