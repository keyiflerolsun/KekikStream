# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper
from Kekik.Sifreleme import AESManager
import json

class MixPlayHD(ExtractorBase):
    name     = "MixPlayHD"
    main_url = "https://mixplayhd.com"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        self.httpx.headers.update({"Referer": referer or self.main_url})

        resp = await self.httpx.get(url)
        match = HTMLHelper(resp.text).regex_first(r"bePlayer\('([^']+)',\s*'(\{[^\}]+\})'\);", group=None)
        if not match:
            raise ValueError(f"MixPlayHD: bePlayer bulunamadı. {url}")

        pass_val, data_val = match
        try:
            data = json.loads(AESManager.decrypt(data_val, pass_val))
            v_url = HTMLHelper(data.get("schedule", {}).get("client", "")).regex_first(r'"video_location":"([^"]+)"')
            if v_url:
                return ExtractResult(name=self.name, url=v_url, referer=self.main_url)
        except Exception as e:
            raise ValueError(f"MixPlayHD: Decryption failed. {e}")

        raise ValueError(f"MixPlayHD: Video URL bulunamadı. {url}")
