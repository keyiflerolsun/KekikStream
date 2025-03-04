# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult

class MailRuExtractor(ExtractorBase):
    name     = "MailRu"
    main_url = "https://my.mail.ru"

    async def extract(self, url, referer=None) -> ExtractResult:
        vid_id         = url.split("video/embed/")[-1].strip()
        video_meta_url = f"{self.main_url}/+/video/meta/{vid_id}"

        if referer:
            self.httpx.headers.update({"Referer": referer})

        istek = await self.httpx.get(video_meta_url)
        istek.raise_for_status()

        video_key = istek.cookies.get("video_key")
        if not video_key:
            raise ValueError("Video key bulunamadı.")

        video_data = istek.json()
        videos     = video_data.get("videos", [])
        if not videos:
            raise ValueError("Videolar bulunamadı.")

        video     = videos[0]
        video_url = video["url"]
        if video_url.startswith("//"):
            video_url = f"https:{video_url}"

        await self.close()
        return ExtractResult(
            name      = self.name,
            url       = video_url,
            referer   = self.main_url,
            headers   = {"Cookie": f"video_key={video_key}"},
            subtitles = []
        )