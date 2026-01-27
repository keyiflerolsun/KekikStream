# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
from Kekik.Sifreleme  import Packer
import re

class VidHide(ExtractorBase):
    name     = "VidHide"
    main_url = "https://vidhidepro.com"

    # Birden fazla domain destekle
    supported_domains = [
        "vidhidepro.com", "vidhide.com", "rubyvidhub.com", 
        "vidhidevip.com", "vidhideplus.com", "vidhidepre.com", 
        "movearnpre.com", "oneupload.to",
        "filelions.live", "filelions.online", "filelions.to",
        "kinoger.be",
        "smoothpre.com",
        "dhtpre.com",
        "peytonepre.com"
    ]

    def can_handle_url(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)

    def get_embed_url(self, url: str) -> str:
        if "/d/" in url:
            return url.replace("/d/", "/v/")
        elif "/download/" in url:
            return url.replace("/download/", "/v/")
        elif "/file/" in url:
            return url.replace("/file/", "/v/")
        elif "/embed/" in url:
            return url.replace("/embed/", "/v/")
        else:
            return url.replace("/f/", "/v/")

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        base_url = self.get_base_url(url)
        self.httpx.headers.update({
            "Referer" : referer or base_url,
            "Origin"  : base_url,
        })
        
        embed_url = self.get_embed_url(url)
        istek     = await self.httpx.get(embed_url, follow_redirects=True)
        text      = istek.text

        # Silinmiş dosya kontrolü
        if "File is no longer available" in text or "File Not Found" in text:
             raise ValueError(f"VidHide: Video silinmiş. {url}")

        # JS Redirect Kontrolü (OneUpload vb.)
        if js_redirect := HTMLHelper(text).regex_first(r"window\.location\.replace\(['\"]([^'\"]+)['\"]\)") or \
                          HTMLHelper(text).regex_first(r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]"):
            # Redirect url'i al
            target_url = js_redirect
            # Bazen path relative olabilir ama genelde full url
            if not target_url.startswith("http"):
                 # urljoin gerekebilir ama şimdilik doğrudan deneyelim veya fix_url
                 target_url = self.fix_url(target_url) # fix_url base'e göre düzeltebilir mi? ExtractorBase.fix_url genelde şema ekler.
                 pass

            # Yeniden istek at
            istek = await self.httpx.get(target_url, headers={"Referer": embed_url}, follow_redirects=True)
            text  = istek.text

        sel       = HTMLHelper(text)

        unpacked = ""
        # Eval script bul (regex ile daha sağlam)
        if eval_match := sel.regex_first(r'(eval\s*\(\s*function[\s\S]+?)<\/script>'):
            try:
                unpacked = Packer.unpack(eval_match)
                if "var links" in unpacked:
                     unpacked = unpacked.split("var links")[1]
            except:
                pass
        
        content  = unpacked or text

        # Regex: Kotlin mantığı (: "url")
        # Ayrıca sources: [...] mantığını da ekle
        m3u8_url = HTMLHelper(content).regex_first(r'sources:\s*\[\s*\{\s*file:\s*"([^"]+)"')

        if not m3u8_url:
            # Genel arama (hls:, file: vb.)
            # Kotlin Regex: :\s*"(.*?m3u8.*?)"
            match = HTMLHelper(content).regex_first(r':\s*["\']([^"\']+\.m3u8[^"\']*)["\']')
            if match:
                m3u8_url = match

        if not m3u8_url:
             # Son şans: herhangi bir m3u8 linki
             m3u8_url = HTMLHelper(content).regex_first(r'["\']([^"\']+\.m3u8[^"\']*)["\']')

        if not m3u8_url:
            raise ValueError(f"VidHide: Video URL bulunamadı. {url}")

        return ExtractResult(
            name       = self.name,
            url        = self.fix_url(m3u8_url),
            referer    = f"{base_url}/",
            user_agent = self.httpx.headers.get("User-Agent", "")
        )
