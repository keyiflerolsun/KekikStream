# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper
import re

class GoodStream(ExtractorBase):
    name     = "GoodStream"
    main_url = "https://goodstream.one"

    supported_domains = ["goodstream.one", "goodstream.tv"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        # 1) Get the embed page
        headers = {
            "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Referer"    : referer or self.main_url,
        }
        resp = await self.async_cf_get(url, headers=headers)

        # 2) Find the file code and POST to /dl
        # document.forms['F1'].file_code.value = code;
        code = self._media_id_from_url(url)
        if not code:
            code = HTMLHelper(resp.text).regex_first(r'file_code\.value\s*=\s*["\']([^"\']+)["\']')

        if not code:
             raise ValueError(f"GoodStream: File code bulunamadı. {url}")

        dl_url = f"{self.get_base_url(url)}/dl"
        data = {
            "op"        : "embed",
            "file_code" : code,
            "auto"      : "1",
            "referer"   : referer or "",
        }

        # We need the same headers for POST
        headers["Origin"]  = self.get_base_url(url)
        headers["Referer"] = url

        dl_resp = await self.async_cf_post(dl_url, headers=headers, data=data)

        # 3) Parse the final m3u8 URL from the response
        # sources: [{file:"..."}]
        m3u8_url = HTMLHelper(dl_resp.text).regex_first(r'sources:\s*\[{file:["\']([^"\']+)["\']')

        if not m3u8_url:
            # Fallback for simple file: "..."
            m3u8_url = HTMLHelper(dl_resp.text).regex_first(r'file\s*:\s*["\']([^"\']+)["\']')

        if not m3u8_url:
            raise ValueError(f"GoodStream: Video URL bulunamadı. {url}")

        return ExtractResult(
            name    = self.name,
            url     = self.fix_url(m3u8_url),
            referer = url
        )

    def _media_id_from_url(self, url: str) -> str | None:
        # Match /e/code or /embed-code or /embed/code
        match = re.search(r"/(?:e|embed-|embed/|embed)/?([0-9a-zA-Z]+)", url)
        if match:
            return match.group(1)
        return None
