# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult


class HexLoad(ExtractorBase):
    name     = "HexLoad"
    main_url = "https://hexload.com"

    supported_domains = ["hexload.com", "hexupload.net"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        vid_id = url.rstrip("/").split("-")[-1].replace(".html", "")

        await self.async_cf_get(url, timeout=12)

        post_data = {
            "op"          : "download3",
            "id"          : vid_id,
            "ajax"        : "1",
            "method_free" : "1",
            "dataType"    : "json",
        }
        headers = {
            "Referer"          : url,
            "X-Requested-With" : "XMLHttpRequest",
            "Content-Type"     : "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept"           : "application/json, text/javascript, */*; q=0.01",
        }

        resp = await self.async_cf_post(f"{self.main_url}/download", data=post_data, headers=headers, timeout=12)
        data = resp.json()

        if data.get("msg") != "OK" or "result" not in data:
            raise ValueError(f"HexLoad: Video bulunamadı. {url}")

        video_url = data["result"]["url"]

        return ExtractResult(
            name    = self.name,
            url     = video_url,
            referer = f"{self.main_url}/",
        )
