# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult

class MailRu(ExtractorBase):
    name     = "MailRu"
    main_url = "https://my.mail.ru"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        v_id = url.split("video/embed/")[-1].strip()
        if referer: self.httpx.headers.update({"Referer": referer})

        resp = await self.httpx.get(f"{self.main_url}/+/video/meta/{v_id}")
        data = resp.json()
        
        v_url = data.get("videos", [{}])[0].get("url")
        if not v_url:
            raise ValueError(f"MailRu: Video URL bulunamadı. {url}")

        return ExtractResult(name=self.name, url=self.fix_url(v_url), referer=self.main_url)
