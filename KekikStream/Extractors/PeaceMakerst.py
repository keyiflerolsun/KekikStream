# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper
import json

class PeaceMakerst(ExtractorBase):
    name     = "PeaceMakerst"
    main_url = "https://peacemakerst.com"

    supported_domains = ["peacemakerst.com", "hdstreamable.com"]

    def can_handle_url(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        self.httpx.headers.update({
            "Referer"          : referer or url,
            "X-Requested-With" : "XMLHttpRequest"
        })

        resp = await self.httpx.post(f"{url}?do=getVideo", data={"hash": url.split("video/")[-1], "r": referer or "", "s": ""})
        data = resp.json()

        m3u8_url = None
        if "teve2.com.tr" in resp.text:
            v_id = HTMLHelper(resp.text).regex_first(r"teve2\.com\.tr\\\/embed\\\/(\d+)")
            t_resp = await self.httpx.get(f"https://www.teve2.com.tr/action/media/{v_id}")
            t_data = t_resp.json()
            m3u8_url = f"{t_data['Media']['Link']['ServiceUrl']}//{t_data['Media']['Link']['SecurePath']}"
        elif sources := data.get("videoSources"):
            m3u8_url = sources[-1]["file"]

        if not m3u8_url:
            raise ValueError(f"PeaceMakerst: Video linki bulunamadı. {url}")

        return ExtractResult(name=self.name, url=m3u8_url, referer=url)