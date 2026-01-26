# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
import json

class VideoSeyred(ExtractorBase):
    name     = "VideoSeyred"
    main_url = "https://videoseyred.in"

    async def extract(self, url: str, referer: str = None) -> list[ExtractResult] | ExtractResult:
        v_id = url.split("embed/")[1].split("?")[0]
        if len(v_id) > 10:
            resp = await self.httpx.get(url)
            v_id = HTMLHelper(resp.text).regex_first(r"playlist\/(.*)\.json")

        json_resp = await self.httpx.get(f"{self.main_url}/playlist/{v_id}.json")
        data = json_resp.json()[0]

        subtitles = [
            Subtitle(name=t["label"], url=self.fix_url(t["file"]))
            for t in data.get("tracks", []) if t.get("kind") == "captions"
        ]

        results = [
            ExtractResult(name=self.name, url=self.fix_url(s["file"]), referer=self.main_url, subtitles=subtitles)
            for s in data.get("sources", [])
        ]

        if not results:
            raise ValueError(f"VideoSeyred: Video bulunamadı. {url}")

        return results[0] if len(results) == 1 else results