# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper
from Kekik.Sifreleme import AESManager
import json

class MixPlayHD(ExtractorBase):
    name     = "MixPlayHD"
    main_url = "https://mixplayhd.com"

    async def extract(self, url, referer=None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        istek = await self.httpx.get(url)
        istek.raise_for_status()

        hp = HTMLHelper(istek.text)
        be_player_matches = hp.regex_all(r"bePlayer\('([^']+)',\s*'(\{[^\}]+\})'\);")
        if not be_player_matches:
            raise ValueError("bePlayer not found in the response.")

        be_player_pass, be_player_data = be_player_matches[0]

        try:
            decrypted_data = AESManager.decrypt(be_player_data, be_player_pass).replace("\\", "")
            decrypted_json = json.loads(decrypted_data)
        except Exception as hata:
            raise RuntimeError(f"Decryption failed: {hata}") from hata

        client_str = decrypted_json.get("schedule", {}).get("client", "")
        video_url = HTMLHelper(client_str).regex_first(r'"video_location":"([^"]+)"')
        if video_url:
            return ExtractResult(
                name      = self.name,
                url       = video_url,
                referer   = self.main_url,
                subtitles = []
            )
        else:
            raise ValueError("M3U8 video URL not found in the decrypted data.")