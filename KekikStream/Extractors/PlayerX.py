# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
import re

class PlayerX(ExtractorBase):
    name              = "PlayerX"
    main_url          = "https://playerx.info"
    supported_domains = ["playerx.info"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        self.httpx.headers.update({
            "Referer" : referer or "https://jetfilmizle.net/",
            "Origin"  : referer or "https://jetfilmizle.net",
        })

        resp   = await self.httpx.get(url)
        html   = resp.text
        origin = f"{resp.url.scheme}://{resp.url.host}"

        # sources: [{file: "watch/187/...", type: "hls"}]
        source_match = re.search(r'sources:\s*\[\{\s*file:\s*"([^"]+)"', html)
        if not source_match:
            raise ValueError(f"PlayerX: Source bulunamadı. {url}")

        video_url = source_match.group(1)
        if not video_url.startswith("http"):
            video_url = f"{origin}/{video_url}"

        # tracks: [{file: "...", label: "...", kind: "captions"}]
        subtitles = []
        for track in re.finditer(
            r'file:\s*"([^"]+)"[^}]*?label:\s*"([^"]+)"[^}]*?kind:\s*"captions"',
            html,
            re.DOTALL,
        ):
            sub_url  = track.group(1)
            sub_name = track.group(2)
            if not sub_url.startswith("http"):
                sub_url = f"{origin}/{sub_url}"
            subtitles.append(Subtitle(name=sub_name.strip(), url=sub_url))

        return ExtractResult(
            name      = self.name,
            url       = video_url,
            referer   = origin,
            subtitles = subtitles,
        )
