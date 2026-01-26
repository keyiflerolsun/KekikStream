# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
from Kekik.Sifreleme   import Packer, StreamDecoder
import json, contextlib

class CloseLoad(ExtractorBase):
    name     = "CloseLoad"
    main_url = "https://closeload.filmmakinesi.to"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        self.httpx.headers.update({
            "Referer" : referer or self.main_url,
            "Origin"  : self.main_url
        })

        resp = await self.httpx.get(url)
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
        
        # 2. Packed Script Fallback
        if not m3u8_url:
            if packed := sel.regex_first(r"(eval\(function\(p,a,c,k,e,d\).+?)\s*</script>"):
                m3u8_url = StreamDecoder.extract_stream_url(Packer.unpack(packed))

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
