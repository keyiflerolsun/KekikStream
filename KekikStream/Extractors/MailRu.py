# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
from httpx            import AsyncClient
import json

class MailRuExtractor(ExtractorBase):
    name     = "MailRu"
    main_url = "https://my.mail.ru"

    async def extract(self, url, referer=None) -> ExtractResult:
        """Mail.Ru URL'sinden medya bilgilerini çıkarır."""
        vid_id         = url.split("video/embed/")[-1].strip()
        video_meta_url = f"{self.main_url}/+/video/meta/{vid_id}"

        async with AsyncClient() as client:
            response = await client.get(video_meta_url, headers={"Referer": url} if referer else {})
            response.raise_for_status()

            video_key = response.cookies.get("video_key")
            if not video_key:
                raise ValueError("Video key bulunamadı.")

            video_data = json.loads(response.text)
            videos     = video_data.get("videos", [])
            if not videos:
                raise ValueError("Videolar bulunamadı.")

            video     = videos[0]
            video_url = video["url"]
            if video_url.startswith("//"):
                video_url = f"https:{video_url}"

            return ExtractResult(
                name      = self.name,
                url       = video_url,
                referer   = self.main_url,
                subtitles = [],
                headers   = {"Cookie": f"video_key={video_key}"}
            )