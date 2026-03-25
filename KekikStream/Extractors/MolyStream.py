# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
import re

class MolyStream(ExtractorBase):
    name     = "MolyStream"
    main_url = "https://dbx.molystream.org"

    # Birden fazla domain destekle
    supported_domains = [
        "dbx.molystream.org", "ydx.molystream.org", "molystream.org",
        "yd.sheila.stream", "ydf.popcornvakti.net", "rufiiguta.com",
    ]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        headers = {
            "Referer"    : referer or self.main_url,
            "User-Agent" : "Mozilla/5.0 (X11; Linux x86_64; rv:101.0) Gecko/20100101 Firefox/101.0",
        }
        self.httpx.headers.update(headers)

        istek  = await self.httpx.get(url, follow_redirects=True)
        html   = istek.text
        secici = HTMLHelper(html)

        # video#sheplayer source ile doğrudan video URL
        v_url = secici.select_attr("video#sheplayer source", "src")

        # Fallback: file/source regex
        if not v_url:
            v_url = secici.regex_first(r'(?:file|source)\s*[:=]\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']')

        # Altyazılar
        subtitles = []
        for s_url, s_name in secici.regex_all(r"addSrtFile\(['\"]([^'\"]+\.srt)['\"]\s*,\s*['\"][a-z]{2}['\"]\s*,\s*['\"]([^'\"]+)['\"]"):
            subtitles.append(Subtitle(name=s_name, url=self.fix_url(s_url)))

        # Video URL bulunamadıysa embed URL'yi WebView için döndür
        final_url = v_url or url

        return ExtractResult(
            name       = self.name,
            url        = final_url,
            referer    = referer or self.main_url,
            user_agent = "Mozilla/5.0 (X11; Linux x86_64; rv:101.0) Gecko/20100101 Firefox/101.0",
            subtitles  = subtitles
        )
