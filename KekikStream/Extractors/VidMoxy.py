# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
from httpx            import AsyncClient
from Kekik.Sifreleme  import Packer, HexCodec
import re

class VidMoxy(ExtractorBase):
    name     = "VidMoxy"
    main_url = "https://vidmoxy.com"

    async def extract(self, url, referer=None) -> ExtractResult:
        self.oturum.headers.update({"User-Agent":"Mozilla/5.0"})
        if referer:
            self.oturum.headers.update({"Referer": referer})

        istek = await self.oturum.get(url)
        istek.raise_for_status()

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
            subtitles = []
        )