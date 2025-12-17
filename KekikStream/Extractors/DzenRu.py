# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
import re

class DzenRu(ExtractorBase):
    name     = "DzenRu"
    main_url = "https://dzen.ru"

    async def extract(self, url, referer=None) -> ExtractResult:
        video_key = url.split("/")[-1]
        video_url = f"{self.main_url}/embed/{video_key}"

        if referer:
            self.httpx.headers.update({"Referer": referer})

        istek = await self.httpx.get(video_url)
        istek.raise_for_status()

        # okcdn.ru linklerini bul
        matches = re.findall(r'https://vd\d+\.okcdn\.ru/\?[^"\'\\\s]+', istek.text)

        if not matches:
            raise ValueError("DzenRu video link not found")

        # Benzersiz linkleri al, son kaliteyi kullan
        unique_links = list(set(matches))
        best_link    = unique_links[-1] if unique_links else None

        if not best_link:
            raise ValueError("No valid video URL found")

        return ExtractResult(
            name      = self.name,
            url       = best_link,
            referer   = self.main_url,
            headers   = {},
            subtitles = []
        )
