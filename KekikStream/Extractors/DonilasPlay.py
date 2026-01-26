# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
from Kekik.Sifreleme   import AESManager
import json, contextlib

class DonilasPlay(ExtractorBase):
    name     = "DonilasPlay"
    main_url = "https://donilasplay.com"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        self.httpx.headers.update({"Referer": referer or url})

        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)

        m3u8_url  = None
        subtitles = []

        # 1. bePlayer (AES)
        if be_match := sel.regex_first(r"bePlayer\('([^']+)',\s*'(\{[^}]+\})'\);", group=None):
            pass_val, data_val = be_match
            with contextlib.suppress(Exception):
                data = json.loads(AESManager.decrypt(data_val, pass_val))
                m3u8_url = data.get("video_location")
                for sub in data.get("strSubtitles", []):
                    if "Forced" not in sub.get("label", ""):
                        subtitles.append(Subtitle(name=sub.get("label"), url=self.fix_url(sub.get("file"))))

        # 2. Fallback
        if not m3u8_url:
            m3u8_url = sel.regex_first(r'file:"([^"]+)"')
            if tracks_match := sel.regex_first(r'tracks:\[([^\]]+)'):
                with contextlib.suppress(Exception):
                    for track in json.loads(f"[{tracks_match}]"):
                        if "Forced" not in track.get("label", ""):
                            subtitles.append(Subtitle(name=track.get("label"), url=self.fix_url(track.get("file"))))

        if not m3u8_url:
            raise ValueError(f"DonilasPlay: Video linki bulunamadı. {url}")

        return ExtractResult(name=self.name, url=m3u8_url, referer=url, subtitles=subtitles)
