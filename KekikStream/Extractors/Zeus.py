# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper

class Zeus(ExtractorBase):
    name     = "Zeus"
    main_url = "https://d2rs.com"

    async def extract(self, url: str, referer: str = None) -> list[ExtractResult]:
        # Iframe içeriğini al
        istek = await self.httpx.get(url, headers={"Referer": referer} if referer else None)
        text  = istek.text

        # 'q' parametresini bul
        # form.append("q", "...")
        q_param = HTMLHelper(text).regex_first(r'form\.append\("q",\s*"([^"]+)"\)')

        if not q_param:
            raise ValueError(f"Zeus: 'q' parametresi bulunamadı. {url}")

        # API'ye POST at
        resp = await self.httpx.post(
            url     = "https://d2rs.com/zeus/api.php",
            data    = {"q": q_param},
            headers = {"Referer": url}
        )

        try:
            sources = resp.json()
        except:
             raise ValueError("Zeus: API yanıtı geçersiz JSON")

        results = []
        # [{"file": "...", "label": "Full HD", "type": "video/mp4"}, ...]
        for i, source in enumerate(sources, 1):
            file_path = source.get("file")
            label     = source.get("label") or ""
            type_     = source.get("type", "")

            if not file_path:
                continue

            full_url = f"https://d2rs.com/zeus/{file_path}"

            # İsimlendirme
            if label:
                source_name = f"{self.name} | {label}"
            else:
                source_name = f"{self.name} | Kaynak {i}"

            results.append(ExtractResult(
                name       = source_name,
                url        = self.fix_url(full_url),
                referer    = url,
                user_agent = self.httpx.headers.get("User-Agent", "")
            ))

        if not results:
            raise ValueError("Zeus: Kaynak bulunamadı")

        return results
