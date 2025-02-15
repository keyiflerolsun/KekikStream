# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult

class MolyStream(ExtractorBase):
    name     = "MolyStream"
    main_url = "https://dbx.molystream.org"

    async def extract(self, url, referer=None) -> ExtractResult:
        return ExtractResult(
            name      = self.name,
            url       = url,
            referer   = url.replace("/sheila", ""),
            headers   = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:101.0) Gecko/20100101 Firefox/101.0"},
            subtitles = []
        )