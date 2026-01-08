# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import ExtractorBase, ExtractResult, HTMLHelper
from Kekik.Sifreleme   import Packer

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
        secici   = HTMLHelper(response)

        # Eğer iframe varsa, iframe'e git
        iframe_src = secici.select_attr("iframe", "src")
        
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
                unpacked_sec = HTMLHelper(unpacked)
                m3u8_url = unpacked_sec.regex_first(r'sources:\[\{file:"(.*?)"')
        else:
            # Iframe varsa devam et
            iframe_url = self.fix_url(iframe_src)
            iframe_headers = default_headers.copy()
            iframe_headers["Accept-Language"] = "en-US,en;q=0.5"
            
            istek    = await self.httpx.get(iframe_url, headers=iframe_headers)
            response = istek.text
            secici   = HTMLHelper(response)
            
            script_data = ""
            for script in secici.select("script"):
                if "function(p,a,c,k,e,d)" in script.text():
                    script_data = script.text()
                    break
            
            if script_data:
                unpacked = Packer.unpack(script_data)
                unpacked_sec = HTMLHelper(unpacked)
                m3u8_url = unpacked_sec.regex_first(r'sources:\[\{file:"(.*?)"')

        if not m3u8_url:
            # Son çare: Normal response içinde ara
            resp_sec = HTMLHelper(response)
            m3u8_url = resp_sec.regex_first(r'sources:\s*\[\s*\{\s*file:\s*"([^"]+)"') or resp_sec.regex_first(r'file:\s*"([^\"]*?\.m3u8[^"]*)"')

        if not m3u8_url:
            raise ValueError(f"Filemoon: Video URL bulunamadı. {url}")

        return ExtractResult(
            name      = self.name,
            url       = self.fix_url(m3u8_url),
            referer   = f"{self.main_url}/",
            user_agent = default_headers["User-Agent"],
            subtitles = []
        )
