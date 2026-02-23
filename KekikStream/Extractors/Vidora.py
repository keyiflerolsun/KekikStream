# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PackedJSExtractor, ExtractResult, HTMLHelper, M3U8_FILE_REGEX

class Vidora(PackedJSExtractor):
    name        = "Vidora"
    main_url    = "https://vidora.stream"
    url_pattern = M3U8_FILE_REGEX

    supported_domains = [
        "vidora.stream",
        "vidora.su",
    ]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        embed_url = url.replace("/download/", "/e/")
        headers   = {
            "Referer"         : referer or self.main_url,
            "Accept-Language" : "en-US,en;q=0.5",
            "Sec-Fetch-Dest"  : "iframe",
        }

        istek  = await self.httpx.get(embed_url, headers=headers, follow_redirects=True)
        secici = HTMLHelper(istek.text)

        # Iframe varsa takip et
        iframe_src = secici.select_attr("iframe", "src")
        if iframe_src:
            istek  = await self.httpx.get(self.fix_url(iframe_src), headers=headers, follow_redirects=True)

        m3u8_url = self.unpack_and_find(istek.text)
        if not m3u8_url:
            raise ValueError(f"Vidora: Video URL bulunamadı. {url}")

        return ExtractResult(
            name    = self.name,
            url     = self.fix_url(m3u8_url),
            referer = f"{self.main_url}/"
        )
