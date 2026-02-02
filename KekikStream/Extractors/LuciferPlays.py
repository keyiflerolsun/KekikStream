# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
from Kekik.Sifreleme  import AESManager
import json, contextlib

class LuciferPlays(ExtractorBase):
    name     = "LuciferPlays"
    main_url = "https://luciferplays.com"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        # LuciferPlays genelde referer olarak kendi ana dizinini veya gömüldüğü sayfayı bekler
        self.httpx.headers.update({"Referer": referer or url})

        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)

        m3u8_url  = None
        subtitles = []

        # 1. bePlayer (AES Decryption)
        # patern: bePlayer('pass', '{"ct":"...", "iv":"...", "s":"..."}');
        if match := sel.regex_first(r"bePlayer\('([^']+)',\s*'(\{[^}]+\})'\);", group=None):
            pass_val, data_val = match
            with contextlib.suppress(Exception):
                decrypted = AESManager.decrypt(data_val, pass_val)

                # Çözülen içerik genelde JSON formatındadır
                try:
                    data = json.loads(decrypted)

                    # Video Lokasyonu (Donilas/HDMom Style)
                    m3u8_url = data.get("video_location")

                    # Altyazılar
                    for sub in data.get("strSubtitles", []):
                        sub_url = self.fix_url(sub.get("file"))
                        if sub_url and "Forced" not in sub.get("label", ""):
                            subtitles.append(Subtitle(
                                name = sub.get("label", "TR").upper(), 
                                url  = sub_url
                            ))

                    # Eğer video_location bulunamadıysa MixPlay style kontrol et
                    if not m3u8_url:
                        client_data = data.get("schedule", {}).get("client", "")
                        m3u8_url = HTMLHelper(client_data).regex_first(r'"video_location":"([^"]+)"')

                except json.JSONDecodeError:
                    # JSON değilse düz metin içinde ara
                    m3u8_url = HTMLHelper(decrypted).regex_first(r'"video_location":"([^"]+)"')

        # 2. Fallback (Düz JS içinde file ara)
        if not m3u8_url:
            m3u8_url = sel.regex_first(r'file\s*:\s*"([^"]+)"')

        if not m3u8_url:
            raise ValueError(f"LuciferPlays: Video linki bulunamadı. {url}")

        return ExtractResult(
            name      = self.name, 
            url       = self.fix_url(m3u8_url), 
            referer   = url, 
            subtitles = subtitles
        )
