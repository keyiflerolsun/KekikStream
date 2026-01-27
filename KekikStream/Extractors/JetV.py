# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper
import json, re

class JetV(ExtractorBase):
    name     = "JetV"
    main_url = "https://jetv.xyz"

    async def extract(self, url: str, referer: str = None) -> list[ExtractResult]:
        istek = await self.httpx.get(url, headers={"Referer": referer} if referer else None)
        text  = istek.text

        # Script içindeki sources kısmını bul
        # "sources": [ ... ]
        sources_str = HTMLHelper(text).regex_first(r'"sources":\s*(\[.*?\])')
        if not sources_str:
             # Altenatif: sources: [ ... ] (tırnaksız sources)
             sources_str = HTMLHelper(text).regex_first(r'sources:\s*(\[.*?\])')

        if not sources_str:
            raise ValueError(f"JetV: Sources bulunamadı. {url}")

        # file: -> "file":
        clean_json = re.sub(r'(\w+):', r'"\1":', sources_str)
        # ' -> "
        clean_json = clean_json.replace("'", '"')

        try:
            sources = json.loads(clean_json)
        except:
            # Basit parser yetmediyse, manuel parse deneyelim (tek kaynak varsa)
            file_url = HTMLHelper(sources_str).regex_first(r'file["\']?:\s*["\']([^"\']+)["\']')
            label    = HTMLHelper(sources_str).regex_first(r'label["\']?:\s*["\']([^"\']+)["\']')
            if file_url:
                sources = [{"file": file_url, "label": label or "Unknown"}]
            else:
                raise ValueError("JetV: JSON parse hatası")

        results = []
        for source in sources:
            file_path = source.get("file")
            label     = source.get("label", "Unknown")

            if not file_path:
                continue

            results.append(ExtractResult(
                name       = f"{self.name} | {label}",
                url        = self.fix_url(file_path),
                referer    = url,
                user_agent = self.httpx.headers.get("User-Agent", "")
            ))

        return results
