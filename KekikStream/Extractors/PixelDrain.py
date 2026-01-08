# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper

class PixelDrain(ExtractorBase):
    name     = "PixelDrain"
    main_url = "https://pixeldrain.com"

    async def extract(self, url, referer=None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        hp = HTMLHelper(url)
        matches = hp.regex_all(r"/u/([^/?]+)|([^\/]+)(?=\?download)")
        if not matches:
            raise ValueError("PixelDrain bağlantısından ID çıkarılamadı.")

        m = matches[0]
        pixel_id = next((g for g in m if g), None)
        download_link = f"{self.main_url}/api/file/{pixel_id}?download"
        referer_link  = f"{self.main_url}/u/{pixel_id}?download"

        return ExtractResult(
            name      = f"{self.name} - {pixel_id}",
            url       = download_link,
            referer   = referer_link,
            subtitles = []
        )