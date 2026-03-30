# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import SecuredLinkExtractor, ExtractResult
import contextlib, json

class HDLoad(SecuredLinkExtractor):
    name     = "HDLoad"
    main_url = "https://hdload.site"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        ref      = referer or self.main_url
        v_id     = self._parse_video_id(url)
        base_url = self._get_base_url(url)

        resp    = await self.async_cf_post(
            url     = f"{base_url}/player/index.php?data={v_id}&do=getVideo",
            data    = {"hash": v_id, "r": ref},
            headers = {"Referer": ref, "X-Requested-With": "XMLHttpRequest"}
        )

        m3u8_url = None
        with contextlib.suppress(json.JSONDecodeError, ValueError):
            payload = resp.json()
            if isinstance(payload, dict):
                m3u8_url = payload.get("securedLink") or payload.get("videoSource")

        if not m3u8_url:
            m3u8_url = self._extract_link_from_text(resp.text)

        if not m3u8_url:
            raise ValueError(f"{self.name}: Video URL bulunamadı. {url}")

        m3u8_url = self.fix_url(m3u8_url)

        return ExtractResult(name=self.name, url=m3u8_url, referer=ref)
