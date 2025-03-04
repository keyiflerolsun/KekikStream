# ! Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
import json, re

class VideoSeyred(ExtractorBase):
    name     = "VideoSeyred"
    main_url = "https://videoseyred.in"

    async def extract(self, url, referer=None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        video_id  = url.split("embed/")[1].split("?")[0]
        if len(video_id) > 10:
            kontrol = await self.httpx.get(url)
            kontrol.raise_for_status()

            video_id = re.search(r"playlist\/(.*)\.json", kontrol.text)[1]

        video_url = f"{self.main_url}/playlist/{video_id}.json"

        response = await self.httpx.get(video_url)
        response.raise_for_status()

        try:
            if response_list := json.loads(response.text):
                response_data = response_list[0]
            else:
                raise ValueError("Empty response from VideoSeyred.")

        except (json.JSONDecodeError, IndexError) as hata:
            raise RuntimeError(f"Failed to parse response: {hata}") from hata

        subtitles = [
            Subtitle(name=track["label"], url=self.fix_url(track["file"]))
                for track in response_data.get("tracks", [])
                    if track.get("kind") == "captions" and track.get("label")
        ]

        if video_links := [
            ExtractResult(
                name      = self.name,
                url       = self.fix_url(source["file"]),
                referer   = self.main_url,
                headers   = {},
                subtitles = subtitles,
            )
                for source in response_data.get("sources", [])
        ]:
            # En yüksek kaliteli videoyu döndür (varsayılan olarak ilk video)
            return video_links[0] if len(video_links) == 1 else video_links
        else:
            raise ValueError("No video links found in the response.")