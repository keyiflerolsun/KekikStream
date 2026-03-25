# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper

class LuluStream(ExtractorBase):
    name     = "LuluStream"
    main_url = "https://luluvdo.com"

    supported_domains = ["lulustream.com", "luluvdo.com", "luluview.com", "luluvid.com", "ponmody.com"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        domain = self.get_base_url(url)
        resp   = await self.httpx.post(
            url  = f"{domain}/dl",
            data = {
                "op"        : "embed",
                "file_code" : url.split("/")[-1],
                "auto"      : "1",
                "referer"   : referer or ""
            },
            headers = {
                "Referer"    : url,
                "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            }
        )
        secici = HTMLHelper(resp.text)

        # Check for direct file link in scripts
        script_content = None
        for s in secici.select("script"):
            txt = s.text()
            if "vplayer" in txt or "sources:" in txt:
                script_content = txt
                break

        video_url = None
        if script_content:
            video_url = secici.regex_first(r'sources\s*:\s*\[\s*["\']([^"\']+)["\']', target=script_content)
            if not video_url:
                video_url = secici.regex_first(r'file\s*:\s*["\']([^"\']+)["\']', target=script_content)
            if not video_url:
                video_url = secici.regex_first(r'src\s*:\s*["\']([^"\']+)["\']', target=script_content)

        # Fallback regex search in whole page
        if not video_url:
            video_url = secici.regex_first(r'sources\s*:\s*\[\s*["\']([^"\']+)["\']')
        if not video_url:
            video_url = secici.regex_first(r'file\s*:\s*["\']([^"\']+)["\']')

        if not video_url:
            raise ValueError(f"LuluStream: Video URL bulunamadı. {url}")

        return ExtractResult(
            name       = self.name,
            url        = video_url,
            referer    = url,
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        )
