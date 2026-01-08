# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
from Kekik.Sifreleme  import Packer, HexCodec

class VidMoxy(ExtractorBase):
    name     = "VidMoxy"
    main_url = "https://vidmoxy.com"

    async def extract(self, url, referer=None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        istek = await self.httpx.get(url)
        istek.raise_for_status()

        subtitles        = []
        subtitle_matches = HTMLHelper(istek.text).regex_all(r'captions","file":"([^\"]+)","label":"([^\"]+)"')
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

        escaped_hex = HTMLHelper(istek.text).regex_first(r'file": "(.*)",')
        if not escaped_hex:
            eval_jwsetup = HTMLHelper(istek.text).regex_first(r'\};\s*(eval\(function[\s\S]*?)var played = \d+;')
            jwsetup      = Packer.unpack(Packer.unpack(eval_jwsetup)) if eval_jwsetup else None
            if jwsetup:
                escaped_hex  = HTMLHelper(jwsetup).regex_first(r'file":"(.*)","label')

        m3u_link = HexCodec.decode(escaped_hex)

        return ExtractResult(
            name      = self.name,
            url       = m3u_link,
            referer   = self.main_url,
            subtitles = subtitles
        )