# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PackedJSExtractor, ExtractResult, HTMLHelper, M3U8_FILE_REGEX

class Filemoon(PackedJSExtractor):
    name        = "Filemoon"
    main_url    = "https://filemoon.to"
    url_pattern = M3U8_FILE_REGEX

    # Filemoon'un farklı domainlerini destekle
    supported_domains = [
        "filemoon.to",
        "filemoon.in",
        "filemoon.sx",
        "filemoon.nl",
        "filemoon.com",
        "bysejikuar.com"
    ]

    _UA = "Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        headers = {
            "Referer"        : url,
            "Sec-Fetch-Dest" : "iframe",
            "Sec-Fetch-Mode" : "navigate",
            "Sec-Fetch-Site" : "cross-site",
            "User-Agent"     : self._UA,
        }
        self.httpx.headers.update(headers)

        try:
            istek = await self.httpx.get(url)
            if len(istek.text) < 5000:
                raise Exception("CF challenge suspected")
        except Exception:
            istek = await self.async_cf_get(url, headers=headers)
        secici = HTMLHelper(istek.text)

        # iframe varsa takip et
        if iframe_src := secici.select_attr("iframe", "src"):
            url   = self.fix_url(iframe_src)
            try:
                istek = await self.httpx.get(url)
                if len(istek.text) < 5000:
                    raise Exception("CF challenge suspected")
            except Exception:
                istek = await self.async_cf_get(url, headers=headers)
            secici = HTMLHelper(istek.text)

        m3u8_url = self.unpack_and_find(istek.text)

        if not m3u8_url:
             # Fallback: m3u8 or mp4 check
             m3u8_url = secici.regex_first(r'file\s*:\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']')

        if not m3u8_url:
            raise ValueError(f"Filemoon: Video URL bulunamadı. {url}")

        return ExtractResult(
            name       = self.name,
            url        = self.fix_url(m3u8_url),
            referer    = f"{self.get_base_url(url)}/",
            user_agent = self._UA,
        )
