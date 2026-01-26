# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper

class PixelDrain(ExtractorBase):
    name     = "PixelDrain"
    main_url = "https://pixeldrain.com"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        if referer: self.httpx.headers.update({"Referer": referer})

        p_id = HTMLHelper(url).regex_first(r"/u/([^/?]+)|([^\/]+)(?=\?download)")
        if not p_id:
            raise ValueError(f"PixelDrain: ID bulunamadı. {url}")

        return ExtractResult(
            name    = f"{self.name} - {p_id}",
            url     = f"{self.main_url}/api/file/{p_id}?download",
            referer = f"{self.main_url}/u/{p_id}?download"
        )