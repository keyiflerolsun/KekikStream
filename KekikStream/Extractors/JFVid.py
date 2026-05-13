# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult

class JFVid(ExtractorBase):
    name     = "JFVid"
    main_url = "https://jfvid.com"

    # Birden fazla domain destekle
    supported_domains = ["jfvid.com", "jetvid.top"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        base_url = self.get_base_url(url)

        # Determine ID from path or query
        if "jetvid.top" in url and "?v=" in url:
            v_id = url.split("?v=")[1].split("&")[0]
        else:
            v_id = url.split("/play/")[-1] if "/play/" in url else url.split("/stream/")[-1]

        return ExtractResult(name=self.name, url=f"{base_url}/stream/{v_id}", referer=referer or base_url)
