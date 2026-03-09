# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper

class Tukipasti(ExtractorBase):
    name     = "Tukipasti"
    main_url = "https://tukipasti.com"

    supported_domains = ["tukipasti.com"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        headers = {
            "Referer"    : referer or self.main_url,
            "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        }

        resp   = await self.httpx.get(url, headers=headers)
        secici = HTMLHelper(resp.text)

        # JWPlayer with turboviplay CDN: <div id="video_player" data-hash="...m3u8">
        video_url = secici.select_attr("#video_player", "data-hash")

        if not video_url:
            # Fallback: var urlPlay = '...m3u8';
            video_url = secici.regex_first(r"var\s+urlPlay\s*=\s*['\"]([^'\"]+)['\"]")

        if not video_url:
            raise ValueError(f"Tukipasti: Video URL bulunamadı. {url}")

        return ExtractResult(
            name    = self.name,
            url     = video_url,
            referer = self.main_url + "/"
        )
