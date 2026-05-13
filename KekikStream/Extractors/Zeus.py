# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper

class Zeus(ExtractorBase):
    name     = "Zeus"
    main_url = "https://d2rs.com"

    async def extract(self, url: str, referer: str = None) -> list[ExtractResult]:
        # Iframe içeriğini al
        headers = {"Referer": referer} if referer else None
        istek   = await self.async_cf_get(url, headers=headers)
        text    = istek.text

        # 'q' parametresini bul
        # form.append("q", "...") or formData.append("q", "...")
        q_param = HTMLHelper(text).regex_first(r'(?s)\.append\(\s*["\']q["\']\s*,\s*["\']([^"\']+)["\']\)')

        if not q_param:
            # Iframe fallback
            iframe_src = HTMLHelper(text).select_attr("iframe", "src")
            if iframe_src:
                return ExtractResult(name=f"{self.name} (Iframe)", url=self.fix_url(iframe_src), referer=url)

            raise ValueError(f"Zeus: 'q' parametresi bulunamadı. {url}")

        # API'ye POST at
        resp = await self.async_cf_post(
            url     = f"{self.main_url}/zeus/api.php",
            data    = {"q": q_param},
            headers = {"Referer": url}
        )

        try:
            sources = resp.json()
        except Exception:
             raise ValueError("Zeus: API yanıtı geçersiz JSON")

        results = []
        # [{"file": "...", "label": "Full HD", "type": "video/mp4"}, ...]
        for i, source in enumerate(sources, 1):
            file_path = source.get("file")
            label     = source.get("label") or ""
            type_     = source.get("type", "")

            if not file_path:
                continue

            full_url = f"{self.main_url}/zeus/{file_path}"

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
