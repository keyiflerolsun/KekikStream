# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
import json, re


class BulguNet(ExtractorBase):
    name     = "BulguNet"
    main_url = "https://bulgu.net"

    supported_domains = ["bulgu.net"]

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        # bulgu.net/okru/embed/TOKEN  -->  player sayfası
        self.httpx.headers.update(
            {
                "Referer" : referer or self.main_url,
                "Origin"  : self.main_url,
            }
        )

        resp = await self.httpx.get(url, follow_redirects=True)
        page = resp.text

        # qualities dizisini JS kaynağından parse et
        # const qualities = [{...}];
        m = re.search(r"const\s+qualities\s*=\s*(\[.*?\]);", page, re.DOTALL)
        if not m:
            raise ValueError("BulguNet: qualities dizisi bulunamadı.")

        try:
            qualities = json.loads(m.group(1))
        except Exception:
            raise ValueError("BulguNet: qualities JSON parse hatası.")

        if not qualities:
            raise ValueError("BulguNet: Kalite listesi boş.")

        # En yüksek kaliteyi seç (son eleman)
        best          = qualities[-1]
        redirect_path = best.get("url", "")

        if not redirect_path:
            raise ValueError("BulguNet: Redirect URL bulunamadı.")

        # Göreceli path ise tam URL yap
        if redirect_path.startswith("/"):
            redirect_url = f"{self.main_url}{redirect_path}"
        else:
            redirect_url = redirect_path

        # Redirect takip ederek gerçek CDN URL'sini al
        cdn_resp = await self.httpx.get(
            redirect_url,
            follow_redirects = True,
            headers          = {
                "Referer" : url,
                "Origin"  : self.main_url,
            },
        )

        # Redirect URL'yi al — str(cdn_resp.url) son konumu verir
        final_url = str(cdn_resp.url)

        if not final_url or final_url == redirect_url:
            raise ValueError("BulguNet: CDN URL alınamadı (redirect başarısız).")

        return ExtractResult(name=self.name, url=self.fix_url(final_url), referer=url)
