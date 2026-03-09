# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PackedJSExtractor, ExtractResult

class DramaCool(PackedJSExtractor):
    name     = "DramaCool"
    main_url = "https://dramacool.men"

    supported_domains = ["dramacool.men"]

    # Unpack sonrası "hls2"/"hls3" ya da herhangi bir m3u8 URL'si
    url_pattern = r'["\'](?:hls\d|file)["\'][:\s]+["\']([^"\']+\.m3u8[^"\']*)["\']'

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        istek = await self.httpx.get(url, headers={"Referer": referer or self.main_url})
        m3u8  = self.unpack_and_find(istek.text)

        if not m3u8:
            raise ValueError(f"DramaCool: m3u8 bulunamadı. {url}")

        return ExtractResult(
            name    = self.name,
            url     = self.fix_url(m3u8),
            referer = self.get_base_url(url) + "/",
        )
