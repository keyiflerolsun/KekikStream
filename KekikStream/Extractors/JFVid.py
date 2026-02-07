# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult

class JFVid(ExtractorBase):
    name     = "JFVid"
    main_url = "https://jfvid.com"

    # Birden fazla domain destekle
    supported_domains = ["jfvid.com"]

    def can_handle_url(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        base_url = self.get_base_url(url)
        v_id     = url.split("/play/")[-1] if "/play/" in url else url.split("/stream/")[-1]

        return ExtractResult(name=self.name, url=f"{base_url}/stream/{v_id}", referer=referer or base_url)
