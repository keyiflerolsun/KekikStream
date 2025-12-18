# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
from Kekik.Sifreleme  import Packer, StreamDecoder
import re

class CloseLoadExtractor(ExtractorBase):
    name     = "CloseLoad"
    main_url = "https://closeload.filmmakinesi.sh"

    async def extract(self, url, referer=None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        istek = await self.httpx.get(url)
        istek.raise_for_status()

        eval_func = re.compile(r'\s*(eval\(function[\s\S].*)\s*').findall(istek.text)[0]
        m3u_link  = StreamDecoder.extract_stream_url(Packer.unpack(eval_func))

        return ExtractResult(
            name      = self.name,
            url       = m3u_link,
            referer   = self.main_url,
            subtitles = []
        )
