# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
from Kekik.Sifreleme  import AESManager
import contextlib, json

class HotStream(ExtractorBase):
    name     = "HotStream"
    main_url = "https://hotstream.club"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        self.httpx.headers.update({"Referer": referer or url})

        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)

        m3u8_url  = None
        subtitles = []

        if match := sel.regex_first(r"bePlayer\('([^']+)',\s*'(\{[^']+\})'\)", group=None):
            pass_val, data_val = match
            with contextlib.suppress(Exception):
                decrypted = AESManager.decrypt(data_val, pass_val)
                try:
                    data = json.loads(decrypted)
                    m3u8_url = data.get("video_location")
                    for sub in data.get("strSubtitles", []):
                        if "Forced" not in sub.get("label", ""):
                            subtitles.append(Subtitle(
                                name = sub.get("label", "TR").upper(),
                                url  = self.fix_url(sub.get("file"))
                            ))
                except json.JSONDecodeError:
                    m3u8_url = HTMLHelper(decrypted).regex_first(r'"video_location":"([^"]+)"')

        if not m3u8_url:
            raise ValueError(f"HotStream: Video linki bulunamadı. {url}")

        return ExtractResult(
            name       = self.name,
            url        = self.fix_url(m3u8_url),
            referer    = url,
            user_agent = self.httpx.headers.get("User-Agent"),
            subtitles  = subtitles
        )
