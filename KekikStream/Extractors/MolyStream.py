# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
from Kekik.Sifreleme import AESManager
import re, json

class MolyStream(ExtractorBase):
    name     = "MolyStream"
    main_url = "https://dbx.molystream.org"

    async def extract(self, url, referer=None) -> ExtractResult:
        return ExtractResult(
            name      = self.name,
            url       = url,
            referer   = url.replace("/sheila", ""),
            subtitles = []
        )