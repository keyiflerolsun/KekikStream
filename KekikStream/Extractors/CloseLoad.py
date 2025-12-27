# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import ExtractorBase, ExtractResult, Subtitle
from Kekik.Sifreleme   import Packer, StreamDecoder
from selectolax.parser import HTMLParser
import re

class CloseLoadExtractor(ExtractorBase):
    name     = "CloseLoad"
    main_url = "https://closeload.filmmakinesi.to"

    async def extract(self, url, referer=None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        istek = await self.httpx.get(url)
        istek.raise_for_status()

        # Video URL'sini çıkar
        eval_func = re.compile(r'\s*(eval\(function[\s\S].*)').findall(istek.text)[0]
        m3u_link  = StreamDecoder.extract_stream_url(Packer.unpack(eval_func))

        # Subtitle'ları parse et (Kotlin referansı: track elementleri)
        subtitles = []
        secici = HTMLParser(istek.text)
        for track in secici.css("track"):
            raw_src = track.attrs.get("src") or ""
            raw_src = raw_src.strip()
            label   = track.attrs.get("label") or track.attrs.get("srclang") or "Altyazı"
            
            if raw_src:
                full_url = raw_src if raw_src.startswith("http") else f"{self.main_url}{raw_src}"
                subtitles.append(Subtitle(name=label, url=full_url))

        return ExtractResult(
            name      = self.name,
            url       = m3u_link,
            referer   = self.main_url,
            subtitles = subtitles
        )
