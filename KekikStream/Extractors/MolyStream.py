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
        if "doctype html" in url:
            secici   = HTMLHelper(url)
            video    = secici.select_attr("video#sheplayer source", "src")
        else:
            video = url

        resp_sec = HTMLHelper(url)
        matches = resp_sec.regex_all(r"addSrtFile\(['\"]([^'\"]+\.srt)['\"]\s*,\s*['\"][a-z]{2}['\"]\s*,\s*['\"]([^'\"]+)['\"]")

        subtitles = [
            Subtitle(name = name, url = self.fix_url(url))
                for url, name in matches
        ]

        return ExtractResult(
            name       = self.name,
            url        = video,
            referer    = video.replace("/sheila", "") if video else None,
            user_agent = "Mozilla/5.0 (X11; Linux x86_64; rv:101.0) Gecko/20100101 Firefox/101.0",
            subtitles  = subtitles
        )
