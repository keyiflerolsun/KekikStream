# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper


class MixDrop(ExtractorBase):
    name     = "MixDrop"
    main_url = "https://mixdrop.co"

    supported_domains = [
        "mixdrop.co", "mixdrop.to", "mixdrop.ps", "mixdrop.ag", "mixdrop.club",
        "mxdrop.to", "mxdrop.ag", "mxdrop.co",
    ]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        domain  = self.get_base_url(url)
        headers = {
            "Referer"    : referer or domain,
            "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        }

        try:
            resp = await self.httpx.get(url, headers=headers)
            html = resp.text
        except Exception:
            resp = await self.async_cf_get(url, headers=headers)
            html = resp.text

        h     = HTMLHelper(html)
        video = (
            h.regex_first(r'(?:vsr|wurl)\s*=\s*["\']([^"\']+)["\']')
            or h.regex_first(r'sources\s*:\s*\[\s*["\']([^"\']+)["\']')
            or h.regex_first(r'file\s*:\s*["\']([^"\']+)["\']')
            or h.regex_first(r'MDCore\.wurl\s*=\s*["\']([^"\']+)["\']')
        )

        if not video:
            raise ValueError(f"MixDrop: Kaynak bulunamadı. {url}")

        if video.startswith("//"):
            video = "https:" + video
        elif video.startswith("/"):
            video = domain + video

        return ExtractResult(
            name       = self.name,
            url        = self.fix_url(video),
            referer    = domain,
            user_agent = headers["User-Agent"]
        )
