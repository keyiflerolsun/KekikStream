# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import ExtractorBase, ExtractResult, HTMLHelper
from Kekik.Sifreleme import AESManager
import contextlib, json

class HDMomPlayer(ExtractorBase):
    name     = "HDMomPlayer"
    main_url = "https://hdmomplayer.com"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        self.httpx.headers.update({"Referer": referer or url})

        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)

        m3u8_url = None
        if match := sel.regex_first(r"bePlayer\('([^']+)',\s*'(\{[^\}]+\})'\);", group=None):
            pass_val, data_val = match
            with contextlib.suppress(Exception):
                decrypted = AESManager.decrypt(data_val, pass_val)
                m3u8_url  = HTMLHelper(decrypted).regex_first(r'video_location":"([^"]+)"')

        if not m3u8_url:
            m3u8_url = sel.regex_first(r'file:"([^"]+)"')

        if not m3u8_url:
            raise ValueError(f"HDMomPlayer: Video linki bulunamadı. {url}")

        return ExtractResult(name=self.name, url=self.fix_url(m3u8_url), referer=url)
