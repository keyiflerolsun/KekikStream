# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
from Kekik.Sifreleme  import Packer
from contextlib       import suppress
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
        "peytonepre.com",
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
        name     = "EarnVids" if any(x in base_url for x in ["smoothpre.com", "dhtpre.com", "peytonepre.com"]) else self.name

        # Kotlin Headers
        headers = {
            "Sec-Fetch-Dest" : "empty",
            "Sec-Fetch-Mode" : "cors",
            "Sec-Fetch-Site" : "cross-site",
            "Origin"         : f"{base_url}/",
            "Referer"        : referer or f"{base_url}/",
        }

        embed_url = self.get_embed_url(url)
        istek     = await self.httpx.get(embed_url, headers=headers, follow_redirects=True)
        text      = istek.text

        # Silinmiş dosya kontrolü
        if any(x in text for x in ["File is no longer available", "File Not Found", "Video silinmiş"]):
             raise ValueError(f"{name}: Video silinmiş. {url}")

        # JS Redirect Kontrolü (OneUpload vb.)
        if js_redirect := HTMLHelper(text).regex_first(r"window\.location\.replace\(['\"]([^'\"]+)['\"]\)") or \
                          HTMLHelper(text).regex_first(r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]"):
            target_url = js_redirect
            if not target_url.startswith("http"):
                 target_url = self.fix_url(target_url)

            istek = await self.httpx.get(target_url, headers={"Referer": embed_url}, follow_redirects=True)
            text  = istek.text

        sel       = HTMLHelper(text)

        unpacked = ""
        # Eval script bul
        if eval_match := sel.regex_first(r'(eval\s*\(\s*function[\s\S]+?)<\/script>'):
            with suppress(Exception):
                unpacked = Packer.unpack(eval_match)
                if "var links" in unpacked:
                     unpacked = unpacked.split("var links")[1]

        content  = unpacked or text

        # Kotlin Exact Regex: :\s*"(.*?m3u8.*?)"
        m3u8_matches = re.findall(r':\s*["\']([^"\']+\.m3u8[^"\']*)["\']', content)

        results = []
        for m3u8_url in m3u8_matches:
            results.append(ExtractResult(
                name       = name,
                url        = self.fix_url(m3u8_url),
                referer    = f"{base_url}/",
                user_agent = self.httpx.headers.get("User-Agent", "")
            ))

        if not results:
            # Fallback for non-m3u8 or different patterns
            if m3u8_url := sel.regex_first(r'sources:\s*\[\s*\{\s*file:\s*"([^"]+)"'):
                results.append(ExtractResult(
                    name       = name,
                    url        = self.fix_url(m3u8_url),
                    referer    = f"{base_url}/",
                    user_agent = self.httpx.headers.get("User-Agent", "")
                ))

        if not results:
            raise ValueError(f"{name}: Video URL bulunamadı. {url}")

        return results[0] if len(results) == 1 else results
