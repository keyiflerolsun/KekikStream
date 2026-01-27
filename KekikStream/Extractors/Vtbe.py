# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper
from Kekik.Sifreleme  import Packer

class Vtbe(ExtractorBase):
    name     = "Vtbe"
    main_url = "https://vtbe.to"

    async def extract(self, url: str, referer: str = None) -> list[ExtractResult]:
        # Iframe ise embed url'i düzeltmek gerekebilir ama genelde embed-xxxx.html formatı
        istek = await self.httpx.get(url, headers={"Referer": referer or self.main_url})
        text  = istek.text

        # Packed script bul: function(p,a,c,k,e,d)
        packed = HTMLHelper(text).regex_first(r'(eval\s*\(\s*function[\s\S]+?)<\/script>')

        if not packed:
            raise ValueError(f"Vtbe: Packed script bulunamadı. {url}")

        unpacked = ""
        try:
            unpacked = Packer.unpack(packed)
        except:
             raise ValueError("Vtbe: Unpack hatası")

        # sources:[{file:"..."
        file_url = HTMLHelper(unpacked).regex_first(r'sources:\s*\[\s*\{\s*file:\s*"([^"]+)"')

        if not file_url:
            raise ValueError("Vtbe: Video URL (file) bulunamadı")

        return ExtractResult(
            name       = self.name,
            url        = self.fix_url(file_url),
            referer    = url,
            user_agent = self.httpx.headers.get("User-Agent", "")
        )
