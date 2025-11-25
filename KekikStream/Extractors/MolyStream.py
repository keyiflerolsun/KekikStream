# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
from parsel           import Selector
import re

class MolyStream(ExtractorBase):
    name     = "MolyStream"
    main_url = "https://dbx.molystream.org"

    async def extract(self, url, referer=None) -> ExtractResult:
        if "doctype html" in url:
            secici = Selector(url)
            video  = secici.css("video#sheplayer source::attr(src)").get()
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
            name      = self.name,
            url       = video,
            referer   = video.replace("/sheila", ""),
            headers   = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:101.0) Gecko/20100101 Firefox/101.0"},
            subtitles = subtitles
        )
