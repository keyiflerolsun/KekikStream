# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult

class YildizKisaFilm(ExtractorBase):
    name     = "YildizKisaFilm"
    main_url = "https://yildizkisafilm.org"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        ref = referer or self.main_url
        v_id = url.split("video/")[-1] if "video/" in url else url.split("?data=")[-1]

        resp = await self.httpx.post(
            f"{self.main_url}/player/index.php?data={v_id}&do=getVideo",
            data    = {"hash": v_id, "r": ref},
            headers = {"Referer": ref, "X-Requested-With": "XMLHttpRequest"}
        )
        
        m3u8_url = resp.json().get("securedLink")
        if not m3u8_url:
            raise ValueError(f"YildizKisaFilm: Video URL bulunamadı. {url}")

        return ExtractResult(name=self.name, url=m3u8_url, referer=ref)
