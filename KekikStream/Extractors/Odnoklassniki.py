# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper
import json, html

class Odnoklassniki(ExtractorBase):
    name     = "Odnoklassniki"
    main_url = "https://odnoklassniki.ru"

    supported_domains = ["odnoklassniki.ru", "ok.ru"]

    def can_handle_url(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        if "/video/" in url:
            url = url.replace("/video/", "/videoembed/")
        self.httpx.headers.update({"Origin": self.main_url})

        resp = await self.httpx.get(url, follow_redirects=True)
        sel  = HTMLHelper(resp.text)

        # Metadata içinden videos array'ini al (esnek regex)
        v_data = sel.regex_first(r'videos[^:]+:(\[.*?\])')
        if not v_data:
            if "Видео заблокировано" in resp.text or "copyrightsRestricted" in resp.text:
                raise ValueError("Odnoklassniki: Video telif nedeniyle silinmiş/erişilemiyor.")
            raise ValueError(f"Odnoklassniki: Video verisi bulunamadı. {url}")

        # Kalite sıralaması (En yüksekten düşüğe)
        order = ["ULTRA", "QUAD", "FULL", "HD", "SD", "LOW", "MOBILE"]
        # Escaped string'i temizle
        v_data = html.unescape(v_data)
        v_data = v_data.replace('\\"', '"').replace('\\/', '/')
        videos = json.loads(v_data)

        best_url = None
        for q in order:
            best_url = next((v.get("url") for v in videos if v.get("name", "").upper() == q), None)
            if best_url:
                break

        if not best_url:
            best_url = videos[0].get("url") if videos else None

        if not best_url:
            raise ValueError("Odnoklassniki: Geçerli video URL'si bulunamadı.")

        # URL temizliği (u0026 -> & ve olası unicode kaçışları)
        best_url = best_url.replace("u0026", "&").replace("\\u0026", "&")
        # Eğer hala \uXXXX formatında unicode kaçışları varsa çöz
        if "\\u" in best_url:
            best_url = best_url.encode().decode('unicode-escape')

        return ExtractResult(name=self.name, url=self.fix_url(best_url), referer=referer)
