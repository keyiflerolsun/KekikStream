# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper
import contextlib

class JetTv(ExtractorBase):
    name     = "JetTv"
    main_url = "https://jetv.xyz"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)

        m3u8_url = None
        final_ref = self.main_url

        if "id=" in url:
            v_id = url.split("id=")[-1]
            with contextlib.suppress(Exception):
                api_resp = await self.httpx.get(f"{self.main_url}/apollo/get_video.php?id={v_id}", headers={"Referer": url})
                data     = api_resp.json()
                if data.get("success"):
                    m3u8_url  = data.get("masterUrl")
                    final_ref = data.get("referrerUrl") or final_ref

        if not m3u8_url:
            m3u8_url = sel.regex_first(r"(?i)file: '([^']*)'")

        if not m3u8_url:
            raise ValueError(f"JetTv: Video URL bulunamadı. {url}")

        return ExtractResult(name=self.name, url=m3u8_url, referer=final_ref)
