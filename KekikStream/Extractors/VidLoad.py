# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
import re


class VidLoad(ExtractorBase):
    name              = "VidLoad"
    main_url          = "https://vidload.site"
    supported_domains = ["vidload.site"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        self.httpx.headers.update(
            {
                "Referer" : referer or self.main_url,
                "Origin"  : self.main_url,
            }
        )

        resp = await self.httpx.get(url)
        html = resp.text

        # JWPlayer file: '...master.m3u8' pattern
        m3u8_match = re.search(r"""file:\s*['"]([^'"]*?master\.m3u8[^'"]*)['"]""", html)
        if not m3u8_match:
            raise ValueError(f"VidLoad: m3u8 URL bulunamadı. {url}")

        base_url = f"{resp.url.scheme}://{resp.url.host}"
        m3u8_url = m3u8_match.group(1)
        if m3u8_url.startswith("/"):
            m3u8_url = f"{base_url}{m3u8_url}"

        # Altyazıları JWPlayer tracks konfigürasyonundan çek
        subtitles = []
        for track in re.finditer(
            r"""file:\s*['"]([^'"]*?\.vtt)['"][^}]*?label:\s*['"]([^'"]+)['"]""",
            html,
            re.DOTALL,
        ):
            sub_url = track.group(1)
            sub_name = track.group(2)
            if sub_url.startswith("/"):
                sub_url = f"{base_url}{sub_url}"
            subtitles.append(Subtitle(name=sub_name, url=sub_url))

        return ExtractResult(
            name      = self.name,
            url       = m3u8_url,
            referer   = base_url,
            subtitles = subtitles,
        )
