# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper

class DzenRu(ExtractorBase):
    name     = "DzenRu"
    main_url = "https://dzen.ru"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        video_key = url.split("/")[-1]
        v_url     = f"{self.main_url}/embed/{video_key}"

        if referer:
            self.httpx.headers.update({"Referer": referer})

        resp = await self.httpx.get(v_url)
        sel  = HTMLHelper(resp.text)

        # Benzersiz okcdn.ru linklerini bul ve en yüksek kaliteyi (genelde sonuncu) seç
        links = sel.regex_all(r'https://vd\d+\.okcdn\.ru/\?[^"\'\\\s]+')
        if not links:
            raise ValueError(f"DzenRu: Video linki bulunamadı. {url}")

        return ExtractResult(name=self.name, url=list(set(links))[-1], referer=self.main_url)
