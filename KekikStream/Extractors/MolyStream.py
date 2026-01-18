# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
import re

class MolyStream(ExtractorBase):
    name     = "MolyStream"
    main_url = "https://dbx.molystream.org"

    # Birden fazla domain destekle
    supported_domains = [
        "dbx.molystream.org",
        "ydx.molystream.org",
        "yd.sheila.stream",
        "ydf.popcornvakti.net",
    ]

    def can_handle_url(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)

    async def extract(self, url, referer=None) -> ExtractResult:
        if "doctype html" in url.lower():
            text = url
        else:
            # Sheila-style referer fix
            if "/embed/sheila/" in url:
                referer = url.replace("/embed/sheila/", "/embed/")

            self.httpx.headers.update({
                "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer"    : referer or self.main_url
            })
            istek = await self.httpx.get(url, follow_redirects=True)
            text  = istek.text

        # 1. Sheila-style links often have the m3u8 directly as the first http line or in script
        m3u8 = None
        if "#EXTM3U" in text:
            for line in text.splitlines():
                line = line.strip().replace('"', '').replace("'", "")
                if line.startswith("http"):
                    m3u8 = line
                    break

        if not m3u8:
            for line in text.splitlines():
                line = line.strip().replace('"', '').replace("'", "")
                if line.startswith("http") and ".m3u8" in line:
                    m3u8 = line
                    break

        if not m3u8:
            secici = HTMLHelper(text)
            # 2. Try video tag
            m3u8 = secici.select_attr("video#sheplayer source", "src") or secici.select_attr("video source", "src")
            
        if not m3u8:
            # 3. Try regex
            m3u8 = HTMLHelper(text).regex_first(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']')

        if not m3u8:
            # Fallback to any http link in a script if it looks like a video link
            m3u8 = HTMLHelper(text).regex_first(r'["\'](https?://[^"\']+/q/\d+)["\']')

        if not m3u8:
            m3u8 = url # Final fallback

        # Subtitles (Sheila style addSrtFile)
        resp_sec = HTMLHelper(text)
        matches = resp_sec.regex_all(r"addSrtFile\(['\"]([^'\"]+\.srt)['\"]\s*,\s*['\"][a-z]{2}['\"]\s*,\s*['\"]([^'\"]+)['\"]")

        subtitles = [
            Subtitle(name = name, url = self.fix_url(url))
                for url, name in matches
        ]

        return ExtractResult(
            name       = self.name,
            url        = m3u8,
            referer    = url,
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            subtitles  = subtitles
        )
