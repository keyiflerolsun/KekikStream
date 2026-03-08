# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper


class FastPlay(ExtractorBase):
    name     = "FastPlay"
    main_url = "https://fastplay.mom"

    supported_domains = ["fastplay.mom"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        ref  = referer or self.main_url
        resp = await self.httpx.get(url, headers={"Referer": ref})
        sel  = HTMLHelper(resp.text)

        stream_url = (
            sel.regex_first(r"const\s+streamUrl\s*=\s*['\"]([^'\"]+)['\"]") or
            sel.regex_first(r"streamUrl\s*=\s*['\"]([^'\"]+)['\"]") or
            sel.regex_first(r"file\s*:\s*streamUrl") and sel.regex_first(r"['\"](/manifests/[^'\"]+)['\"]")
        )
        stream_type = sel.regex_first(r"streamType\s*=\s*['\"]([^'\"]+)['\"]") or "hls"

        if not stream_url:
            raise ValueError(f"FastPlay: Video URL bulunamadı. {url}")

        return ExtractResult(
            name    = f"{self.name} - {stream_type.upper()}",
            url     = self.fix_url(stream_url),
            referer = ref
        )
