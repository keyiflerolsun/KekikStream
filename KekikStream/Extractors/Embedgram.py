# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper

class Embedgram(ExtractorBase):
    name              = "Embedgram"
    main_url          = "https://embedgram.com"
    supported_domains = ["embedgram.com", "upload.embedgram.com"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        istek  = await self.async_cf_get(url, headers={"Referer": referer or self.main_url})
        secici = HTMLHelper(istek.text)

        # 1. Look for direct file in script or config
        media_url = secici.regex_first(r'["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']')

        # 2. Look for iframe
        if not media_url:
            iframe = secici.select_attr("iframe", "src")
            if iframe:
                # Recursive extraction
                return await self.extract(self.fix_url(iframe), referer=url)

        if not media_url:
             raise ValueError(f"Embedgram: Medya bulunamadı. {url}")

        return ExtractResult(
            name    = self.name,
            url     = media_url,
            referer = url
        )
