# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
import json

class TurkeyPlayer(ExtractorBase):
    name     = "TurkeyPlayer"
    main_url = "https://watch.turkeyplayer.com/"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        istek       = await self.httpx.get(url)
        page_content = istek.text

        video_json_str = HTMLHelper(page_content).regex_first(r'(?s)var\s+video\s*=\s*(\{.*?\});')
        if not video_json_str:
             raise ValueError("TurkeyPlayer: Video JSON bulunamadı")

        video_data = json.loads(video_json_str)

        video_id  = video_data.get("id")
        video_md5 = video_data.get("md5")

        master_url = f"https://watch.turkeyplayer.com/m3u8/8/{video_md5}/master.txt?s=1&id={video_id}&cache=1"

        return ExtractResult(
            name       = self.name,
            url        = master_url,
            referer    = referer or url,
            user_agent = self.httpx.headers.get("User-Agent", ""),
            subtitles  = []
        )
