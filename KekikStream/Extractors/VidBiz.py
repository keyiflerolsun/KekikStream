# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper
from Kekik.Sifreleme  import Packer

class VidBiz(ExtractorBase):
    name     = "VidBiz"
    main_url = "https://videolar.biz"

    async def extract(self, url: str, referer: str = None) -> list[ExtractResult]:
        istek = await self.httpx.get(url, headers={"Referer": referer} if referer else None)
        text  = istek.text

        # Eval script bul (kaken içeriyor olmalı)
        eval_script = HTMLHelper(text).regex_first(r'(eval\(function[\s\S]+?)<\/script>') or \
                      HTMLHelper(text).regex_first(r'(eval\(function[\s\S]+)')
        if not eval_script:
            raise ValueError(f"VidBiz: Packed script bulunamadı. {url}")

        unpacked = ""
        try:
            unpacked = Packer.unpack(eval_script)
        except:
             raise ValueError("VidBiz: Unpack hatası")

        # window.kaken="..."
        kaken = HTMLHelper(unpacked).regex_first(r'window\.kaken\s*=\s*"([^"]+)"')
        if not kaken:
            raise ValueError("VidBiz: Kaken token bulunamadı")

        # API POST
        # Content-Type: text/plain önemli olabilir
        resp = await self.httpx.post(
            url     = "https://s2.videolar.biz/api/",
            content = kaken, # data yerine content=raw string
            headers = {"Content-Type": "text/plain", "Referer": url}
        )

        try:
            data = resp.json()
        except:
            raise ValueError("VidBiz: API yanıtı JSON değil")

        if data.get("status") != "ok":
            raise ValueError(f"VidBiz: API hatası {data}")

        results = []
        for source in data.get("sources", []):
            file_url = source.get("file")
            label    = source.get("label", "Unknown")

            if not file_url:
                continue

            results.append(ExtractResult(
                name       = f"{self.name} | {label}",
                url        = self.fix_url(file_url),
                referer    = url,
                user_agent = self.httpx.headers.get("User-Agent", "")
            ))

        return results
