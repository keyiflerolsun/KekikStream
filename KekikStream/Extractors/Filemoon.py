# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
from Kekik.Sifreleme  import Packer
from parsel           import Selector
import re

class Filemoon(ExtractorBase):
    name     = "Filemoon"
    main_url = "https://filemoon.to"

    # Filemoon'un farklı domainlerini destekle
    supported_domains = [
        "filemoon.to",
        "filemoon.in",
        "filemoon.sx",
        "filemoon.nl",
        "filemoon.com"
    ]

    def can_handle_url(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        headers = {
            "Referer"        : url,
            "Sec-Fetch-Dest" : "iframe",
            "Sec-Fetch-Mode" : "navigate",
            "Sec-Fetch-Site" : "cross-site",
        }
        self.httpx.headers.update(headers)

        # İlk sayfayı al
        istek    = await self.httpx.get(url)
        response = istek.text
        secici   = Selector(response)

        # Eğer iframe varsa, iframe'e git
        iframe_src = secici.css("iframe::attr(src)").get()
        if iframe_src:
            iframe_url = self.fix_url(iframe_src)
            self.httpx.headers.update({
                "Accept-Language" : "en-US,en;q=0.5",
                "Sec-Fetch-Dest"  : "iframe"
            })
            istek    = await self.httpx.get(iframe_url)
            response = istek.text

        # Packed script'i bul ve unpack et
        m3u8_url = None

        if Packer.detect_packed(response):
            try:
                unpacked = Packer.unpack(response)
                # sources:[{file:"..." pattern'ını ara
                if match := re.search(r'sources:\s*\[\s*\{\s*file:\s*"([^"]+)"', unpacked):
                    m3u8_url = match.group(1)
                elif match := re.search(r'file:\s*"([^"]*?\.m3u8[^"]*)"', unpacked):
                    m3u8_url = match.group(1)
            except Exception:
                pass

        # Fallback: Doğrudan response'ta ara
        if not m3u8_url:
            if match := re.search(r'sources:\s*\[\s*\{\s*file:\s*"([^"]+)"', response):
                m3u8_url = match.group(1)
            elif match := re.search(r'file:\s*"([^"]*?\.m3u8[^"]*)"', response):
                m3u8_url = match.group(1)

        if not m3u8_url:
            raise ValueError(f"Filemoon: Video URL bulunamadı. {url}")

        return ExtractResult(
            name      = self.name,
            url       = self.fix_url(m3u8_url),
            referer   = f"{self.main_url}/",
            subtitles = []
        )
