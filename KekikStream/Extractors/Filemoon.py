# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import ExtractorBase, ExtractResult
from Kekik.Sifreleme   import Packer
from selectolax.parser import HTMLParser
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
        default_headers = {
            "Referer"         : url,
            "Sec-Fetch-Dest"  : "iframe",
            "Sec-Fetch-Mode"  : "navigate",
            "Sec-Fetch-Site"  : "cross-site",
            "User-Agent"      : "Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0"
        }
        self.httpx.headers.update(default_headers)

        # İlk sayfayı al
        istek    = await self.httpx.get(url)
        response = istek.text
        secici   = HTMLParser(response)

        # Eğer iframe varsa, iframe'e git
        iframe_el = secici.css_first("iframe")
        iframe_src = iframe_el.attrs.get("src") if iframe_el else None
        
        m3u8_url = None
        
        if not iframe_src:
            # Fallback: Script içinde ara (Kotlin: selectFirst("script:containsData(function(p,a,c,k,e,d))"))
            script_data = ""
            for script in secici.css("script"):
                if "function(p,a,c,k,e,d)" in script.text():
                    script_data = script.text()
                    break
            
            if script_data:
                unpacked = Packer.unpack(script_data)
                if match := re.search(r'sources:\[\{file:"(.*?)"', unpacked):
                    m3u8_url = match.group(1)
        else:
            # Iframe varsa devam et
            iframe_url = self.fix_url(iframe_src)
            iframe_headers = default_headers.copy()
            iframe_headers["Accept-Language"] = "en-US,en;q=0.5"
            
            istek    = await self.httpx.get(iframe_url, headers=iframe_headers)
            response = istek.text
            secici   = HTMLParser(response)
            
            script_data = ""
            for script in secici.css("script"):
                if "function(p,a,c,k,e,d)" in script.text():
                    script_data = script.text()
                    break
            
            if script_data:
                unpacked = Packer.unpack(script_data)
                if match := re.search(r'sources:\[\{file:"(.*?)"', unpacked):
                    m3u8_url = match.group(1)

        if not m3u8_url:
            # Son çare: Normal response içinde ara
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
            user_agent = default_headers["User-Agent"],
            subtitles = []
        )
