# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper


class BurstCloud(ExtractorBase):
    name     = "BurstCloud"
    main_url = "https://www.burstcloud.co"

    supported_domains = ["burstcloud.co", "www.burstcloud.co"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        headers = {
            "Referer"    : referer or self.main_url,
            "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        }

        resp   = await self.httpx.get(url, headers=headers)
        secici = HTMLHelper(resp.text)

        file_id = secici.select_attr("#player", "data-file-id")
        if not file_id:
            file_id = secici.regex_first(r'data-file-id=["\'](\d+)')

        if not file_id:
            raise ValueError(f"BurstCloud: File ID bulunamadı. {url}")

        play_resp = await self.httpx.post(
            url     = f"{self.main_url}/file/play-request/",
            headers = headers,
            data    = {"fileId": file_id}
        )

        play_data = play_resp.json()
        if play_data.get("error"):
            raise ValueError(f"BurstCloud: {play_data['error']}. {url}")

        cdn_url = play_data.get("purchase", {}).get("cdnUrl")
        if not cdn_url:
            raise ValueError(f"BurstCloud: CDN URL bulunamadı. {url}")

        return ExtractResult(
            name       = self.name,
            url        = cdn_url,
            referer    = f"{self.main_url}/",
            user_agent = headers["User-Agent"]
        )
