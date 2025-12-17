# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
from Kekik.Sifreleme  import Packer
from parsel           import Selector
import re

class VidHide(ExtractorBase):
    name            = "VidHide"
    main_url        = "https://vidhidepro.com"
    requires_referer = True

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
        if referer:
            self.cffi.headers.update({"Referer": referer})

        self.cffi.headers.update({
            "Sec-Fetch-Dest" : "empty",
            "Sec-Fetch-Mode" : "cors",
            "Sec-Fetch-Site" : "cross-site",
            "Origin"         : self.main_url,
        })
        
        embed_url = self.get_embed_url(url)
        istek     = await self.cffi.get(embed_url)
        response  = istek.text

        script = None
        if "eval(function" in response:
            try:
                unpacked = Packer.unpack(response)
                if "var links" in unpacked:
                    script = unpacked.split("var links")[1]
                else:
                    script = unpacked
            except Exception:
                pass
        
        if not script:
             if matches := re.search(r'sources:\s*(\[.*?\])', response, re.DOTALL):
                 script = matches.group(1)

        m3u8_url = None
        if script:
            # m3u8 urls could be prefixed by 'file:', 'hls2:' or 'hls4:', so we just match ':'
            if match := re.search(r':\s*"([^"]*?m3u8[^"]*?)"', script):
                 m3u8_url = match.group(1)

        if not m3u8_url:
            # Fallback direct search in response if unpacking failed or structure changed
            if match := re.search(r'file:"(.*?\.m3u8.*?)"', response):
                m3u8_url = match.group(1)
        
        if not m3u8_url:
            raise ValueError(f"VidHide: Video URL bulunamadı. {url}")

        return ExtractResult(
            name      = self.name,
            url       = self.fix_url(m3u8_url),
            referer   = f"{self.main_url}/",
            headers   = dict(self.cffi.headers),
            subtitles = []
        )
