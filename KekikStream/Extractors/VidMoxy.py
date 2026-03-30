# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
from Kekik.Sifreleme  import Packer, HexCodec

class VidMoxy(ExtractorBase):
    name              = "VidMoxy"
    main_url          = "https://vidmoxy.com"
    supported_domains = ["vidmoxy.com", "vidmoxy.net", "vidmoxy.biz", "vidmoxy.to"]

    def can_handle_url(self, url: str) -> bool:
        return "vidmoxy" in url

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        # Try multiple times if needed or use cf
        resp = await self.async_cf_get(url)
        sel  = HTMLHelper(resp.text)

        subtitles = []
        # JSON approach for subtitles
        for s_url, s_lang in sel.regex_all(r'captions","file":"([^\"]+)","label":"([^\"]+)"'):
            decoded_lang = s_lang.encode().decode('unicode_escape')
            subtitles.append(Subtitle(name=decoded_lang, url=s_url.replace("\\", "")))

        # Direct Hex data
        hex_data = sel.regex_first(r'file": "(.*)",') or sel.regex_first(r'file":"([^"]+)"')

        if not hex_data:
            # Unpack approach
            eval_data = sel.regex_first(r'\};\s*(eval\(function[\s\S]*?)var played = \d+;')
            if eval_data:
                unpacked = Packer.unpack(Packer.unpack(eval_data))
                hex_data = HTMLHelper(unpacked).regex_first(r'file":"(.*)","label')

        if not hex_data:
            # Fallback to general link extraction
            m3u8 = sel.regex_first(r'["\']?file["\']?\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']')
            if m3u8:
                return ExtractResult(name=self.name, url=m3u8, referer=url, subtitles=subtitles)
            raise ValueError(f"VidMoxy: Hex data bulunamadı. {url}")

        decoded_url = HexCodec.decode(hex_data) if len(hex_data) > 100 else hex_data

        return ExtractResult(
            name      = self.name,
            url       = decoded_url,
            referer   = url,
            subtitles = subtitles
        )
