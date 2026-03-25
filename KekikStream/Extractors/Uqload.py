# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper

class Uqload(ExtractorBase):
    name     = "Uqload"
    main_url = "https://uqload.cx"

    supported_domains = ["uqload.com", "uqload.io", "uqload.cx", "uqload.to", "uqload.co", "uqload.is"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        domain  = self.get_base_url(url)
        headers = {
            "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        }
        # uqload.is embed kısıtlaması: uqload domain'inden gelen Referer'da kısıtlama yapıyor
        # Sadece dışarıdan gelen referer'ı (plugin sayfası) kullan
        if referer and "uqload" not in referer:
            headers["Referer"] = referer

        try:
            resp    = await self.httpx.get(url, headers=headers, follow_redirects=True)
            if "embed restricted" in resp.text:
                headers.pop("Referer", None)
                resp    = await self.httpx.get(url, headers=headers, follow_redirects=True)
            content = resp.text
        except Exception:
            resp    = await self.async_cf_get(url, headers=headers)
            content = resp.text

        secici = HTMLHelper(content)

        # Method 1: script | file: "..."
        video_url = secici.regex_first(r'file\s*:\s*["\']([^"\']+)["\']')

        if not video_url:
            # Method 2: sources: ["..."]
            video_url = secici.regex_first(r'sources\s*:\s*\[\s*["\']([^"\']+)["\']')

        if not video_url:
             video_url = secici.regex_first(r'src\s*:\s*["\']([^"\']+)["\']')

        if not video_url:
            raise ValueError(f"Uqload: Video URL bulunamadı. {url}")

        return ExtractResult(
            name    = self.name,
            url     = video_url,
            referer = domain
        )
