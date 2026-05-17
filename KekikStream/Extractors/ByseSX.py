# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from urllib.parse     import urlparse
from KekikStream.Core import ExtractorBase, ExtractResult

class ByseSX(ExtractorBase):
    name     = "ByseSX"
    main_url = "https://byse.sx"

    supported_domains = [
        "byse.sx",
        "bysesukior.com",
        "bysejikuar.com",
        "bysezoxexe.com",
        "bysezejataos.com",
        "bysebuho.com",
        "bysevepoin.com",
        "byseqekaho.com",
        "bysesx.com",
        "weneverbeenfree.com",
        "subdrc.xyz",
    ]

    _api_url = "http://px-webservisler:2585/api/v1/bflix"

    async def extract(self, url: str, referer: str = None) -> list[ExtractResult] | ExtractResult | None:
        """
        ByseSX / weneverbeenfree.com video oynatıcı akışlarını yerel keyifAPI üzerinden çözer.
        """
        try:
            params = {"url": url}
            if referer:
                params["referer"] = referer

            resp = await self.httpx.get(self._api_url, params=params, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and data.get("results"):
                    results = []
                    for res in data["results"]:
                        results.append(ExtractResult(
                            name    = self.name,
                            url     = res["url"],
                            referer = res["referer"],
                        ))
                    return results if len(results) > 1 else results[0]
        except Exception:
            pass

        return None
