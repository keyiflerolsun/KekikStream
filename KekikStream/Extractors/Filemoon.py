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
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        # Eğer iframe varsa, iframe'e git
        iframe_src = secici.select_attr("iframe", "src")
        m3u8_url   = None
        
        if iframe_src:
            url    = self.fix_url(iframe_src)
            istek  = await self.httpx.get(url)
            secici = HTMLHelper(istek.text)

        # script p,a,c,k,e,d içinde ara
        script_data = secici.regex_first(r"(eval\(function\(p,a,c,k,e,d\).+?)\s*</script>")
        if script_data:
            unpacked = Packer.unpack(script_data)
            m3u8_url = HTMLHelper(unpacked).regex_first(r'sources:\[\{file:"(.*?)"')

        if not m3u8_url:
            # Fallback
            m3u8_url = secici.regex_first(r'sources:\s*\[\s*\{\s*file:\s*"([^"]+)"') or secici.regex_first(r'file:\s*"([^\"]*?\.m3u8[^"]*)"')

        if not m3u8_url:
            raise ValueError(f"Filemoon: Video URL bulunamadı. {url}")

        return ExtractResult(
            name       = self.name,
            url        = self.fix_url(m3u8_url),
            referer    = f"{self.get_base_url(url)}/",
            user_agent = default_headers["User-Agent"]
        )
