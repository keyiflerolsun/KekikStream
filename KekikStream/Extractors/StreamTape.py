# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper


class StreamTape(ExtractorBase):
    name              = "StreamTape"
    main_url          = "https://streamtape.com"
    supported_domains = ["streamtape.com", "streamtape.to", "streamtape.net", "strtape.cloud", "strcloud.in"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        self.httpx.headers.update(
            {
                "Referer": referer or self.main_url,
            }
        )

        resp = await self.httpx.get(url, follow_redirects=True)
        html = resp.text

        sel = HTMLHelper(html)

        # robotlink innerHTML pattern:
        # getElementById('robotlink').innerHTML = '//streamtape.com/get'+ ('xcd_video?id=...&token=...').substring(2).substring(1)
        match = sel.regex_first(
            r"getElementById\('robotlink'\)\.innerHTML\s*=\s*'([^']+)'\s*\+\s*\('([^']+)'\)",
            group=None,
        )
        if not match:
            raise ValueError(f"StreamTape: robotlink pattern bulunamadı. {url}")

        base_part, token_part = match

        # JavaScript'in .substring(2).substring(1) → Python [3:]
        video_url = f"https:{base_part}{token_part[3:]}"

        # Redirect'i takip et (get_video → gerçek mp4 URL)
        head_resp = await self.httpx.head(video_url, follow_redirects=True)
        final_url = str(head_resp.url)

        return ExtractResult(
            name      = self.name,
            url       = final_url,
            referer   = self.main_url,
            subtitles = [],
        )
