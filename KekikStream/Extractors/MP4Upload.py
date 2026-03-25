# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper


class MP4Upload(ExtractorBase):
    name     = "MP4Upload"
    main_url = "https://www.mp4upload.com"

    supported_domains = ["mp4upload.com", "www.mp4upload.com"]

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
            h.regex_first(r'player\.src\(\s*\{\s*(?:type:.*?,)?\s*src:\s*["\']([^"\']+)["\']')
            or h.regex_first(r'player\.src\(["\']([^"\']+)["\']\)')
            or h.regex_first(r'file\s*:\s*["\']([^"\']+)["\']')
            or h.regex_first(r'sources\s*:\s*\[\s*["\']([^"\']+)["\']')
        )

        if not video:
            raise ValueError(f"MP4Upload: Kaynak bulunamadı. {url}")

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
