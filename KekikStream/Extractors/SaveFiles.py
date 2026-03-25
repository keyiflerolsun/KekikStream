# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
import re


class SaveFiles(ExtractorBase):
    name     = "SaveFiles"
    main_url = "https://savefiles.com"

    supported_domains = ["savefiles.com"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        vid_id = url.rstrip("/").rsplit("/", 1)[-1]

        post_data = {
            "op"        : "embed",
            "file_code" : vid_id,
            "auto"      : "1",
            "referer"   : referer or "",
        }

        resp = await self.async_cf_get(url, timeout=12)
        resp = await self.async_cf_post(
            f"{self.main_url}/dl",
            data    = post_data,
            headers = {"Referer" : url},
            timeout = 12,
        )

        m3u8_match = re.search(r'file\s*:\s*["\']([^"\']+\.m3u8[^"\']*)["\']', resp.text)
        if not m3u8_match:
            raise ValueError(f"SaveFiles: m3u8 bulunamadı. {url}")

        return ExtractResult(
            name    = self.name,
            url     = m3u8_match.group(1),
            referer = f"{self.main_url}/",
        )
