# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult

class HDPlayerSystem(ExtractorBase):
    name     = "HDPlayerSystem"
    main_url = "https://hdplayersystem.com"

    async def extract(self, url, referer=None) -> ExtractResult:
        ext_ref = referer or ""

        if "video/" in url:
            vid_id = url.split("video/")[-1]
        else:
            vid_id = url.split("?data=")[-1]

        post_url = f"{self.main_url}/player/index.php?data={vid_id}&do=getVideo"

        response = await self.cffi.post(
            url     = post_url,
            data    = {"hash": vid_id, "r": ext_ref},
            headers = {
                "Referer"          : ext_ref,
                "Content-Type"     : "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With" : "XMLHttpRequest"
            }
        )
        response.raise_for_status()

        video_data = response.json()
        m3u_link   = video_data.get("securedLink")

        if not m3u_link:
            raise ValueError("securedLink not found in response")

        return ExtractResult(
            name      = self.name,
            url       = m3u_link,
            referer   = url,
            headers   = {},
            subtitles = []
        )
