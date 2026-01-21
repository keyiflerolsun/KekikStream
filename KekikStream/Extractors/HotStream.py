# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper
from Kekik.Sifreleme import AESManager
import re
import json

class HotStream(ExtractorBase):
    name     = "HotStream"
    main_url = "https://hotstream.club"

    async def extract(self, url: str, referer: str = None) -> ExtractResult | None:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        istek = await self.httpx.get(url)
        html = istek.text
        helper = HTMLHelper(html)

        m = re.search(r"bePlayer\('([^']+)',\s*'(\{[^']+\})'\)", html)
        if not m:
             # Try double quotes just in case
             m = re.search(r'bePlayer\("([^"]+)",\s*"(\{[^"]+\})"\)', html)
             
        if m:
            pass_val = m.group(1)
            data_val = m.group(2)
            
            try:
                decrypted = AESManager.decrypt(data_val, pass_val)
                if decrypted:
                    decrypted = decrypted.replace("\\", "")
                    # Search for video_location in decrypted string
                    m_loc = re.search(r'"video_location":"([^"]+)"', decrypted)
                    if m_loc:
                        video_url = m_loc.group(1).replace(r"\/", "/")
                        return ExtractResult(
                            name    = self.name,
                            url     = video_url,
                            referer = url
                        )
            except Exception:
                pass

        return None
