# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
import re

class PixelDrain(ExtractorBase):
    name     = "PixelDrain"
    main_url = "https://pixeldrain.com"

    async def extract(self, url, referer=None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        pixel_id_match = re.search(r"/u/([^/?]+)|([^\/]+)(?=\?download)", url)
        if not pixel_id_match:
            raise ValueError("PixelDrain bağlantısından ID çıkarılamadı.")

        pixel_id      = pixel_id_match[1]
        download_link = f"{self.main_url}/api/file/{pixel_id}?download"
        referer_link  = f"{self.main_url}/u/{pixel_id}?download"

        await self.close()
        return ExtractResult(
            name      = f"{self.name} - {pixel_id}",
            url       = download_link,
            referer   = referer_link,
            headers   = {},
            subtitles = []
        )