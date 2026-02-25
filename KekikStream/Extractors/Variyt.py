# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
import re

class Variyt(ExtractorBase):
    name     = "Variyt"
    main_url = "https://variyt.ws"

    supported_domains = ["variyt.ws"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        resp    = await self.async_cf_get(url, headers={"Referer": referer or self.main_url})
        content = resp.text

        # Prioritize HLS over DASH/DASHA
        v_match = re.search(r'hls[\'\"]?\s*:\s*[\'\"](.*?)[\'\"]', content) or \
                  re.search(r'(?:dash|dasha)[\'\"]?\s*:\s*[\'\"](.*?)[\'\"]', content)

        if not v_match:
            return None

        return ExtractResult(
            name    = self.name,
            url     = self.fix_url(v_match.group(1).replace('\\/', '/')),
            referer = url
        )
