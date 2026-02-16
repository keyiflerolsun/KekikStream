# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

"""
videoUrl / videoServer pattern'i kullanan Extractor'lar için ortak base class.

SetPlay, ExPlay gibi siteler aynı JS yapısını kullanır:
- HTML içinde videoUrl / videoServer regex ile parse
- ?partKey query parametresinden dil bilgisi
- Sonuç: base_url + videoUrl + ?s=videoServer
"""

from .ExtractorBase   import ExtractorBase
from .ExtractorModels import ExtractResult
from ..Helpers        import HTMLHelper
from urllib.parse     import urlparse, parse_qs


class VideoPlayerExtractor(ExtractorBase):
    """
    videoUrl + videoServer pattern'i kullanan Extractor'lar için ortak base class.

    Alt sınıflarda sadece şunları tanımlamanız yeterli:
        name, main_url (ve opsiyonel: supported_domains, strip_query)

    Opsiyonel override alanları:
        strip_query : bool  — URL'den query string'i kaldır (default: False)
        lower_key   : bool  — partKey'i lowercase'e çevir (default: False)
    """

    strip_query: bool = False
    lower_key:   bool = False

    def _resolve_suffix(self, sel: HTMLHelper, part_key: str) -> str:
        """partKey veya title'dan dil/suffix bilgisini çıkar."""
        key = part_key.lower() if self.lower_key else part_key

        if "turkcedublaj" in key.lower():
            return "Dublaj"
        if "turkcealtyazi" in key.lower():
            return "Altyazı"

        if part_key:
            return part_key

        title = sel.regex_first(r'title":"([^",]+)"')
        if title:
            return title.split(".")[-1]

        return "Bilinmiyor"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        self.httpx.headers.update({"Referer": referer or url})

        request_url = url.split("?")[0] if self.strip_query else url
        resp = await self.httpx.get(request_url)
        sel  = HTMLHelper(resp.text)

        v_url = sel.regex_first(r'videoUrl":"([^",]+)"')
        v_srv = sel.regex_first(r'videoServer":"([^",]+)"')
        if not v_url or not v_srv:
            raise ValueError(f"{self.name}: Video url/server bulunamadı. {url}")

        params   = parse_qs(urlparse(url).query)
        part_key = params.get("partKey", [""])[0]
        suffix   = self._resolve_suffix(sel, part_key)

        base = self.get_base_url(url) if not self.strip_query else self.main_url

        return ExtractResult(
            name    = f"{self.name} - {suffix}",
            url     = f"{base}{v_url.replace(chr(92), '')}?s={v_srv}",
            referer = request_url,
        )
