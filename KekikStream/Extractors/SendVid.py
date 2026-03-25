# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper


class SendVid(ExtractorBase):
    name     = "SendVid"
    main_url = "https://sendvid.com"

    supported_domains = ["sendvid.com"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        headers = {
            "Referer"    : referer or self.main_url,
            "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        }

        resp   = await self.httpx.get(url, headers=headers)
        secici = HTMLHelper(resp.text)

        video_url = secici.select_attr("source", "src")

        if not video_url:
            video_url = secici.regex_first(r'var\s+video_source\s*=\s*["\']([^"\']+)')

        if not video_url:
            raise ValueError(f"SendVid: Video URL bulunamadı. {url}")

        return ExtractResult(
            name       = self.name,
            url        = video_url,
            referer    = f"{self.main_url}/",
            user_agent = headers["User-Agent"]
        )
