# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
import re, json

class PeaceMakerst(ExtractorBase):
    name     = "PeaceMakerst"
    main_url = "https://peacemakerst.com"

    async def extract(self, url, referer=None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        self.httpx.headers.update({
            "Content-Type"     : "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With" : "XMLHttpRequest"
        })

        response = await self.httpx.post(
            url  = f"{url}?do=getVideo",
            data = {
                "hash" : url.split("video/")[-1],
                "r"    : referer or "",
                "s"    : ""
            }
        )
        response.raise_for_status()

        response_text = response.text
        m3u_link      = None

        if "teve2.com.tr\\/embed\\/" in response_text:
            teve2_id = re.search(r"teve2\.com\.tr\\\/embed\\\/(\d+)", response_text)[1]
            teve2_url = f"https://www.teve2.com.tr/action/media/{teve2_id}"

            teve2_response = await self.httpx.get(teve2_url, headers={"Referer": f"https://www.teve2.com.tr/embed/{teve2_id}"})
            teve2_response.raise_for_status()
            teve2_json = teve2_response.json()

            m3u_link = f"{teve2_json['Media']['Link']['ServiceUrl']}//{teve2_json['Media']['Link']['SecurePath']}"
        else:
            try:
                video_response = response.json()
                if video_sources := video_response.get("videoSources", []):
                    m3u_link = video_sources[-1]["file"]
            except (json.JSONDecodeError, KeyError) as hata:
                raise ValueError("Peace response is invalid or null.") from hata

        if not m3u_link:
            raise ValueError("m3u link not found.")

        return ExtractResult(
            name      = self.name,
            url       = m3u_link,
            referer   = url,
            headers   = {},
            subtitles = []
        )