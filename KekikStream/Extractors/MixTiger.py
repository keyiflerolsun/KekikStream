# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult

class MixTiger(ExtractorBase):
    name     = "MixTiger"
    main_url = "https://www.mixtiger.com"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        ref = referer or self.main_url
        v_id = url.split("video/")[-1] if "video/" in url else ""

        resp = await self.httpx.post(
            f"{url}?do=getVideo",
            data    = {"hash": v_id, "r": ref, "s": ""},
            headers = {
                "Referer": ref,
                "X-Requested-With": "XMLHttpRequest"
            }
        )
        data = resp.json()

        m3u8_url = data.get("videoSrc")
        if not m3u8_url and data.get("videoSources"):
            m3u8_url = data["videoSources"][-1].get("file")

        if not m3u8_url:
            raise ValueError(f"MixTiger: Video linki bulunamadı. {url}")

        return ExtractResult(
            name    = self.name,
            url     = m3u8_url,
            referer = None if "disk.yandex" in m3u8_url else ref
        )
