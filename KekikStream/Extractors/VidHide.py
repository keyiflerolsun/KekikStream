# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
from Kekik.Sifreleme  import Packer
import re

class VidHide(ExtractorBase):
    name     = "VidHide"
    main_url = "https://vidhidepro.com"

    # Birden fazla domain destekle
    supported_domains = ["vidhidepro.com", "vidhide.com", "rubyvidhub.com"]

    def can_handle_url(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)

    def get_embed_url(self, url: str) -> str:
        if "/d/" in url:
            return url.replace("/d/", "/v/")
        elif "/download/" in url:
            return url.replace("/download/", "/v/")
        elif "/file/" in url:
            return url.replace("/file/", "/v/")
        else:
            return url.replace("/f/", "/v/")

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        base_url = self.get_base_url(url)
        self.httpx.headers.update({
            "Referer" : referer or base_url,
            "Origin"  : base_url,
        })
        
        embed_url = self.get_embed_url(url)
        istek     = await self.httpx.get(embed_url)
        sel       = HTMLHelper(istek.text)

        unpacked = ""
        if "eval(function" in istek.text:
            try:
                unpacked = Packer.unpack(istek.text)
            except:
                pass
        
        content  = unpacked or istek.text
        m3u8_url = HTMLHelper(content).regex_first(r'[:"]\s*["\']([^"\']+\.m3u8[^"\']*)["\']')

        if not m3u8_url:
            raise ValueError(f"VidHide: Video URL bulunamadı. {url}")

        return ExtractResult(
            name       = self.name,
            url        = self.fix_url(m3u8_url),
            referer    = f"{base_url}/",
            user_agent = self.httpx.headers.get("User-Agent", "")
        )
