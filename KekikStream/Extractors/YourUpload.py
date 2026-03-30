# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper

class YourUpload(ExtractorBase):
    name     = "YourUpload"
    main_url = "https://www.yourupload.com"

    supported_domains = ["yourupload.com"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        if "/embed/" not in url and "/watch/" in url:
            url = url.replace("/watch/", "/embed/")

        headers = {
            "Referer"    : referer or self.main_url,
            "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        }

        resp = await self.httpx.get(url, headers=headers)
        sel  = HTMLHelper(resp.text)

        # Look for file link in script or og:video
        video_url = sel.select_attr("meta[property='og:video']", "content") or \
                    sel.select_attr("meta[property='og:video:url']", "content")

        if not video_url:
            video_url = sel.regex_first(r"file\s*:\s*['\"]([^'\"]+)['\"]")

        if not video_url:
            # Fallback to direct mp4 link if found
            video_url = sel.regex_first(r'["\']?url["\']?\s*:\s*["\']([^"\']+\.mp4[^"\']*)["\']')

        if not video_url:
            raise ValueError(f"YourUpload: Video URL bulunamadı. {url}")

        return ExtractResult(
            name       = self.name,
            url        = self.fix_url(video_url),
            referer    = url,
            user_agent = headers["User-Agent"]
        )
