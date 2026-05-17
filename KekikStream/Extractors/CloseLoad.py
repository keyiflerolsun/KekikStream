# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PackedJSExtractor, ExtractResult, Subtitle, HTMLHelper
import json, contextlib

class CloseLoad(PackedJSExtractor):
    name     = "CloseLoad"
    main_url = "https://closeload.filmmakinesi.to"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        headers = {
            "Referer" : referer or self.main_url,
            "Origin"  : self.main_url
        }

        resp = await self.async_cf_get(url, headers=headers)
        sel  = HTMLHelper(resp.text)

        # 1. JSON-LD'den Dene
        m3u8_url = None
        for script in sel.select("script[type='application/ld+json']"):
            with contextlib.suppress(Exception):
                data = json.loads(script.text(strip=True))
                if content_url := data.get("contentUrl"):
                    if content_url.startswith("http"):
                        m3u8_url = content_url
                        break

        # 2. Packed Script Fallback (unpack_and_find ile)
        if not m3u8_url:
            m3u8_url = self.unpack_and_find(resp.text)

        if not m3u8_url:
            raise ValueError(f"CloseLoad: Video URL bulunamadı. {url}")

        subtitles = []
        for track in sel.select("track"):
            src = track.attrs.get("src")
            if src:
                subtitles.append(Subtitle(
                    name = track.attrs.get("label") or track.attrs.get("srclang") or "Altyazı",
                    url  = self.fix_url(src)
                ))

        return ExtractResult(
            name      = self.name,
            url       = m3u8_url,
            referer   = self.main_url,
            subtitles = subtitles
        )
