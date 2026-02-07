# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
from Kekik.Sifreleme  import Packer, HexCodec

class VidMoxy(ExtractorBase):
    name     = "VidMoxy"
    main_url = "https://vidmoxy.com"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)

        subtitles = []
        for s_url, s_lang in sel.regex_all(r'captions","file":"([^\"]+)","label":"([^\"]+)"'):
            decoded_lang = s_lang.encode().decode('unicode_escape')
            subtitles.append(Subtitle(name=decoded_lang, url=s_url.replace("\\", "")))

        hex_data = sel.regex_first(r'file": "(.*)",')
        if not hex_data:
            eval_data = sel.regex_first(r'\};\s*(eval\(function[\s\S]*?)var played = \d+;')
            if eval_data:
                unpacked = Packer.unpack(Packer.unpack(eval_data))
                hex_data = HTMLHelper(unpacked).regex_first(r'file":"(.*)","label')

        if not hex_data:
            raise ValueError(f"VidMoxy: Hex data bulunamadı. {url}")

        return ExtractResult(
            name      = self.name,
            url       = HexCodec.decode(hex_data),
            referer   = self.main_url,
            subtitles = subtitles
        )
