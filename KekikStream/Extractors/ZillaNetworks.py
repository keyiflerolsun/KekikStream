# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult


class ZillaNetworks(ExtractorBase):
    name     = "ZillaNetworks"
    main_url = "https://zilla-networks.com"

    supported_domains = ["zilla-networks.com", "player.zilla-networks.com"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        v_id     = url.split("/")[-1]
        base_url = self.get_base_url(url)
        m3u8_url = f"{base_url}/m3u8/{v_id}"

        return ExtractResult(name=self.name, url=m3u8_url, referer=url)
