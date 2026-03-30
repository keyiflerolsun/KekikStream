# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper

class Netu(ExtractorBase):
    name     = "Netu"
    main_url = "https://hqq.tv"

    supported_domains = [
        "hqq.tv", "hqq.to", "hqq.ac", "hqq.is", "hqq.watch",
        "waaw.to", "waaw.tv", "waaw.ac", "waaw.is", "waaw.watch",
        "netu.tv", "netu.to", "netu.ac", "netu.is"
    ]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        if "/f/" in url:
            url = url.replace("/f/", "/e/")

        headers = {
            "Referer"    : referer or self.main_url,
            "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        }

        # Netu often needs multiple layers or has complex JS
        # For now, we try to get the basic video link or use it as is for WebView
        try:
            resp = await self.httpx.get(url, headers=headers, follow_redirects=True)
        except:
            # Fallback for SSL errors
            resp = await self.async_cf_get(url, headers=headers, verify=False)

        sel = HTMLHelper(resp.text)

        # Look for direct m3u8 or mp4 links
        video_url = sel.regex_first(r'["\']?file["\']?\s*:\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']')

        if not video_url:
            # Check for packed JS
            from Kekik.Sifreleme import Packer
            if packed := sel.regex_first(r'(eval\(function[\s\S]+?)\s*<\/script>'):
                try:
                    unpacked  = Packer.unpack(packed)
                    video_url = HTMLHelper(unpacked).regex_first(r'["\']?file["\']?\s*:\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']')
                except:
                    pass

        # If we can't find a direct link, return the embed URL as the "video" URL
        # (This allows WebView players to still work if they support these domains)
        # But for KekikStream, we want direct links if possible.

        if not video_url:
             # Fallback to a common API endpoint if exists
             pass

        return ExtractResult(
            name       = self.name,
            url        = self.fix_url(video_url) if video_url else url,
            referer    = url,
            user_agent = headers["User-Agent"]
        )
