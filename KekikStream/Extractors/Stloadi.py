# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
import re

class Stloadi(ExtractorBase):
    name     = "Kinogo Player"
    main_url = "https://stloadi.live"

    supported_domains = ["stloadi.live", "kinosource.pw"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        resp    = await self.async_cf_get(url, headers={"Referer": referer or self.main_url})
        content = resp.text

        # Prioritize HLS/FILE over DASH/DASHA
        v_match = re.search(r'(?:hls|file)[\'\"]?\s*:\s*[\'\"](.*?)[\'\"]', content) or \
                  re.search(r'(?:dash|dasha)[\'\"]?\s*:\s*[\'\"](.*?)[\'\"]', content)

        if not v_match:
            return None

        return ExtractResult(
            name    = self.name,
            url     = self.fix_url(v_match.group(1).replace('\\/', '/')),
            referer = url
        )
