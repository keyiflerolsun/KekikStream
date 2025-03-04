# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
from Kekik.Sifreleme  import Packer, HexCodec
import re

class VidMoxy(ExtractorBase):
    name     = "VidMoxy"
    main_url = "https://vidmoxy.com"

    async def extract(self, url, referer=None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        istek = await self.httpx.get(url)
        istek.raise_for_status()

        subtitles        = []
        subtitle_matches = re.findall(r'captions","file":"([^"]+)","label":"([^"]+)"', istek.text)
        seen_subtitles   = set()

        for sub_url, sub_lang in subtitle_matches:
            if sub_url in seen_subtitles:
                continue

            seen_subtitles.add(sub_url)
            decoded_lang = (
                sub_lang.replace("\\u0131", "ı")
                        .replace("\\u0130", "İ")
                        .replace("\\u00fc", "ü")
                        .replace("\\u00e7", "ç")
            )
            subtitles.append(Subtitle(name=decoded_lang, url=sub_url.replace("\\", "")))

        try:
            escaped_hex = re.findall(r'file": "(.*)",', istek.text)[0]
        except Exception:
            eval_jwsetup = re.compile(r'\};\s*(eval\(function[\s\S]*?)var played = \d+;').findall(istek.text)[0]
            jwsetup      = Packer.unpack(Packer.unpack(eval_jwsetup))
            escaped_hex  = re.findall(r'file":"(.*)","label', jwsetup)[0]

        m3u_link = HexCodec.decode(escaped_hex)

        await self.close()
        return ExtractResult(
            name      = self.name,
            url       = m3u_link,
            referer   = self.main_url,
            headers   = {},
            subtitles = subtitles
        )