# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ...CLI                      import konsol
from ..Extractor.ExtractorModels import ExtractResult


class PluginExtractionMixin:
    async def extract(
        self,
        url: str,
        referer: str = None,
        prefix: str | None = None,
        name_override: str | None = None
    ) -> ExtractResult | list[ExtractResult] | None:
        """
        Extractor ile video URL'sini çıkarır.

        Args:
            url           : Iframe veya video URL'si
            referer       : Referer header (varsayılan: plugin main_url)
            prefix        : İsmin başına eklenecek opsiyonel etiket (örn: "Türkçe Dublaj")
            name_override : İsmi tamamen değiştirecek opsiyonel etiket (Extractor adını ezer)

        Returns:
            ExtractResult: Extractor sonucu (name prefix ile birleştirilmiş) veya None

        Extractor bulunamadığında veya hata oluştuğunda uyarı verir.
        """
        if referer is None:
            referer = f"{self.main_url}/"

        extractor = self.ex_manager.find_extractor(url)
        if not extractor:
            konsol.log(f"[magenta][?] {self.name} » Extractor bulunamadı: {url}")
            self.failed_extractions.append({"url" : url, "extractor" : "", "name" : name_override or prefix or "", "error" : "Extractor bulunamadı"})
            return None

        try:
            data = await extractor.extract(url, referer=referer)

            # Liste ise her bir öğe için prefix/override ekle
            if isinstance(data, list):
                for item in data:
                    item.extractor = extractor.name
                    if not item.user_agent:
                        item.user_agent = extractor.httpx.headers.get("User-Agent")
                    if name_override:
                        item.name = name_override
                    elif prefix and item.name:
                        if item.name.lower() in prefix.lower():
                            item.name = prefix
                        else:
                            item.name = f"{prefix} | {item.name}"
                return data

            # Tekil öğe ise
            if data is None:
                return None

            data.extractor = extractor.name
            if not data.user_agent:
                data.user_agent = extractor.httpx.headers.get("User-Agent")
            if name_override:
                data.name = name_override
            elif prefix and data.name:
                if data.name.lower() in prefix.lower():
                    data.name = prefix
                else:
                    data.name = f"{prefix} | {data.name}"

            return data
        except Exception as hata:
            konsol.log(f"[red][!] {self.name} » Extractor hatası ({extractor.name}): {hata}")
            self.failed_extractions.append({"url" : url, "extractor" : extractor.name, "name" : name_override or prefix or "", "error" : str(hata)})
            return None
