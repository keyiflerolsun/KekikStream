# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper

class Vidoza(ExtractorBase):
    name     = "Vidoza"
    main_url = "https://vidoza.net"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        headers = {"Referer": referer or url}
        resp    = await self.async_cf_get(url, headers=headers)
        secici  = HTMLHelper(resp.text)

        # sourcesCode: [{ src: "...", ... }]
        v_url = secici.regex_first(r'sourcesCode\s*:\s*\[\s*{\s*src\s*:\s*["\']([^"\']+)["\']')

        if not v_url:
            # Fallback
            v_url = secici.select_attr("source", "src")

        if not v_url:
            raise ValueError(f"Vidoza: Video bulunamadı. {url}")

        return ExtractResult(name=self.name, url=v_url, referer=url)
