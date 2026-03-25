# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
from urllib.parse     import urlparse, parse_qs

class VideoParktop(ExtractorBase):
    name     = "VideoParktop"
    main_url = "https://videopark.top"

    supported_domains = ["videopark.top"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        qs     = parse_qs(urlparse(url).query)
        vid_id = qs.get("id", [None])[0]

        # /titan/w/{code} formatı için path'den ID çıkar
        if not vid_id:
            path_parts = urlparse(url).path.rstrip("/").split("/")
            if len(path_parts) >= 3 and path_parts[-2] == "w":
                vid_id = path_parts[-1]

        if not vid_id:
            raise ValueError(f"VideoParktop: ID bulunamadı. {url}")

        base_url = self.get_base_url(url)
        api_url  = f"{base_url}/oplayer/reload.php?id={vid_id}&nocache=1"

        resp = await self.httpx.get(api_url, headers={"Referer": url})
        data = resp.json()

        if data.get("error"):
            raise ValueError(f"VideoParktop: API hatası — {data['error']}. {url}")

        # HLS tercih et, yoksa ilk MP4
        hls = (data.get("hlsSource") or {}).get("file")
        if hls:
            return ExtractResult(
                name    = self.name,
                url     = self.fix_url(hls),
                referer = base_url + "/",
            )

        mp4_sources = data.get("mp4Sources") or []
        if mp4_sources:
            best = sorted(mp4_sources, key=lambda x: x.get("height", 0), reverse=True)[0]
            return ExtractResult(
                name    = self.name,
                url     = self.fix_url(best["file"]),
                referer = base_url + "/",
            )

        raise ValueError(f"VideoParktop: Video linki bulunamadı. {url}")
