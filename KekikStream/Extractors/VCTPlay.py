# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
from urllib.parse     import urlparse, parse_qs

class VCTPlay(ExtractorBase):
    name     = "VCTPlay"
    main_url = "https://vctplay.site"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        v_id = url.split("/")[-1].split("?")[0]
        params = parse_qs(urlparse(url).query)
        part_key = params.get("partKey", [""])[0].lower()

        suffix = ""
        if "turkcedublaj" in part_key:
            suffix = "Dublaj"
        elif "turkcealtyazi" in part_key:
            suffix = "Altyazı"

        return ExtractResult(
            name    = f"{self.name} - {suffix}" if suffix else self.name,
            url     = f"{self.main_url}/manifests/{v_id}/master.txt",
            referer = f"{self.main_url}/"
        )
