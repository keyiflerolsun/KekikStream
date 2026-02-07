# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper
import json

class TRsTX(ExtractorBase):
    name     = "TRsTX"
    main_url = "https://trstx.org"

    async def extract(self, url: str, referer: str = None) -> list[ExtractResult] | ExtractResult:
        ref = referer or self.main_url
        self.httpx.headers.update({"Referer": ref})

        resp = await self.httpx.get(url)
        path = HTMLHelper(resp.text).regex_first(r'file":"([^\"]+)')
        if not path:
            raise ValueError(f"TRsTX: File path bulunamadı. {url}")

        post_resp = await self.httpx.post(f"{self.main_url}/{path.replace('\\', '')}")
        data_list = post_resp.json()[1:] if isinstance(post_resp.json(), list) else []

        results = []
        for item in data_list:
            title = item.get("title")
            file  = item.get("file")
            if title and file:
                playlist_resp = await self.httpx.post(f"{self.main_url}/playlist/{file.lstrip('/')}.txt")
                results.append(ExtractResult(
                    name    = f"{self.name} - {title}",
                    url     = playlist_resp.text,
                    referer = self.main_url
                ))

        if not results:
            raise ValueError(f"TRsTX: Video bulunamadı. {url}")

        return results[0] if len(results) == 1 else results
