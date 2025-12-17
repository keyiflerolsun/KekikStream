# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
from Kekik.Sifreleme import AESManager
import re, json

class MixPlayHD(ExtractorBase):
    name     = "MixPlayHD"
    main_url = "https://mixplayhd.com"

    async def extract(self, url, referer=None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        istek = await self.httpx.get(url)
        istek.raise_for_status()

        be_player_match = re.search(r"bePlayer\('([^']+)',\s*'(\{[^\}]+\})'\);", istek.text)
        if not be_player_match:
            raise ValueError("bePlayer not found in the response.")

        be_player_pass = be_player_match[1]
        be_player_data = be_player_match[2]

        try:
            decrypted_data = AESManager.decrypt(be_player_data, be_player_pass).replace("\\", "")
            decrypted_json = json.loads(decrypted_data)
        except Exception as hata:
            raise RuntimeError(f"Decryption failed: {hata}") from hata

        if video_url_match := re.search(
            pattern = r'"video_location":"([^"]+)"',
            string  = decrypted_json.get("schedule", {}).get("client", ""),
        ):
            return ExtractResult(
                name      = self.name,
                url       = video_url_match[1],
                referer   = self.main_url,
                headers   = {},
                subtitles = []
            )
        else:
            raise ValueError("M3U8 video URL not found in the decrypted data.")