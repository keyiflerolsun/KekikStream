# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
from urllib.parse import urlparse, parse_qs
import re

class SetPrime(ExtractorBase):
    name     = "SetPrime"
    main_url = "https://setplay.site"

    async def extract(self, url, referer=None) -> ExtractResult:
        # URL parsing
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        part_key = params.get("partKey", [""])[0].upper()
        clean_url = url.split("?partKey=")[0]
        
        # POST URL: embed?i= -> embed/get?i=
        post_url = clean_url.replace("embed?i=", "embed/get?i=")
        
        response = await self.httpx.post(
            url     = post_url,
            headers = {"Referer": clean_url}
        )
        response.raise_for_status()
        
        # Links parse
        links_match = re.search(r'Links":\["([^"\]]+)"', response.text)
        if not links_match:
            raise ValueError("Links not found in SetPrime response")
            
        link_suffix = links_match.group(1)
        if not link_suffix.startswith("/"):
            raise ValueError("Links not valid (must start with /)")
            
        m3u_link = f"{self.main_url}{link_suffix}"
        
        display_name = f"{self.name} - {part_key}" if part_key else self.name

        return ExtractResult(
            name      = display_name,
            url       = m3u_link,
            referer   = clean_url,
            headers   = {},
            subtitles = []
        )
