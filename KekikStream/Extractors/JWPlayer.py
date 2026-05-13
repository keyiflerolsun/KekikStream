# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult

class JWPlayer(ExtractorBase):
    name              = "JWPlayer"
    main_url          = "https://jwplayer.com"
    supported_domains = ["cdn.jwplayer.com"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        # JWPlayer manifests are usually direct m3u8
        return ExtractResult(
            name    = self.name,
            url     = url,
            referer = referer or self.main_url
        )
