# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult


class ShortICU(ExtractorBase):
    name     = "ShortICU"
    main_url = "https://short.icu"

    supported_domains = ["short.icu", "short.ink", "go.animeyt2.es", "animeyt2.es"]

    async def extract(self, url: str, referer: str = None) -> list[ExtractResult]:
        # Short.icu is usually a redirector
        headers = {"Referer": referer or self.main_url}
        try:
            resp      = await self.httpx.get(url, follow_redirects=True, headers=headers, timeout=15)
            final_url = str(resp.url)

            if final_url != url and "short" not in final_url:
                # Redirected to a new host, try extracting it
                res = await self.ex_manager.extract(final_url, referer=url)
                if res:
                    return res if isinstance(res, list) else [res]
        except:
            pass

        return []
