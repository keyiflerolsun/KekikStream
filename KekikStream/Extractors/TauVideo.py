# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult

class TauVideo(ExtractorBase):
    name     = "TauVideo"
    main_url = "https://tau-video.xyz"

    async def extract(self, url, referer=None) -> list[ExtractResult]:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        video_key = url.split("/")[-1]
        api_url   = f"{self.main_url}/api/video/{video_key}"

        response = await self.httpx.get(api_url)
        response.raise_for_status()

        api_data = response.json()

        if "urls" not in api_data:
            raise ValueError("API yanıtında 'urls' bulunamadı.")

        results = [
                ExtractResult(
                    name      = f"{self.name} - {video['label']}",
                    url       = video["url"],
                    referer   = referer or self.main_url,
                    headers   = {},
                    subtitles = []
                )
                    for video in api_data["urls"]
            ]

        return results[0] if len(results) == 1 else results