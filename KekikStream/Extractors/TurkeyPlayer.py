# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
import re, json

class TurkeyPlayer(ExtractorBase):
    name     = "TurkeyPlayer"
    main_url = "https://watch.turkeyplayer.com/"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})
        
        istek       = await self.httpx.get(url)
        page_content = istek.text

        video_json_match = re.search(r'var\s+video\s*=\s*(\{.*?\});', page_content, re.DOTALL)
        if not video_json_match:
             raise ValueError("TurkeyPlayer: Video JSON bulunamadı")

        video_data = json.loads(video_json_match.group(1))
        
        video_id  = video_data.get("id")
        video_md5 = video_data.get("md5")

        master_url = f"https://watch.turkeyplayer.com/m3u8/8/{video_md5}/master.txt?s=1&id={video_id}&cache=1"
        
        return ExtractResult(
            name      = self.name,
            url       = master_url,
            referer   = referer or url,
            headers   = dict(self.httpx.headers),
            subtitles = []
        )
