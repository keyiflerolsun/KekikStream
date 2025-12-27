# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import ExtractorBase, ExtractResult, Subtitle
from selectolax.parser import HTMLParser
import re

class MolyStream(ExtractorBase):
    name     = "MolyStream"
    main_url = "https://dbx.molystream.org"

    async def extract(self, url, referer=None) -> ExtractResult:
        if "doctype html" in url:
            secici   = HTMLParser(url)
            video_el = secici.css_first("video#sheplayer source")
            video    = video_el.attrs.get("src") if video_el else None
        else:
            video = url

        matches = re.findall(
            pattern = r"addSrtFile\(['\"]([^'\"]+\.srt)['\"]\s*,\s*['\"][a-z]{2}['\"]\s*,\s*['\"]([^'\"]+)['\"]",
            string  = url
        )

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
