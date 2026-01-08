# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
from Kekik.Sifreleme   import Packer, StreamDecoder
import json

class CloseLoadExtractor(ExtractorBase):
    name     = "CloseLoad"
    main_url = "https://closeload.filmmakinesi.to"

    def _extract_from_json_ld(self, html: str) -> str | None:
        """JSON-LD script tag'inden contentUrl'i çıkar (Kotlin versiyonundaki gibi)"""
        secici = HTMLHelper(html)
        for script in secici.select("script[type='application/ld+json']"):
            try:
                data = json.loads(script.text(strip=True))
                if content_url := data.get("contentUrl"):
                    if content_url.startswith("http"):
                        return content_url
            except (json.JSONDecodeError, TypeError):
                # Regex ile contentUrl'i çıkarmayı dene
                if content_url := secici.regex_first(r'"contentUrl"\s*:\s*"([^\"]+)"', script.text()):
                    if content_url.startswith("http"):
                        return content_url
        return None

    def _extract_from_packed(self, html: str) -> str | None:
        """Packed JavaScript'ten video URL'sini çıkar (fallback)"""
        try:
            packed = HTMLHelper(html).regex_all(r'\s*(eval\(function[\s\S].*)')
            if packed:
                return StreamDecoder.extract_stream_url(Packer.unpack(packed[0]))
        except Exception:
            pass
        return None

    async def extract(self, url, referer=None) -> ExtractResult:
        if referer:
            self.httpx.headers.update({"Referer": referer})
        
        self.httpx.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
            "Origin": self.main_url
        })

        istek = await self.httpx.get(url)
        istek.raise_for_status()

        # Önce JSON-LD'den dene (daha güvenilir - Kotlin versiyonu gibi)
        m3u_link = self._extract_from_json_ld(istek.text)
        
        # Fallback: Packed JavaScript'ten çıkar
        if not m3u_link:
            m3u_link = self._extract_from_packed(istek.text)

        if not m3u_link:
            raise Exception("Video URL bulunamadı (ne JSON-LD ne de packed script'ten)")

        # Subtitle'ları parse et (Kotlin referansı: track elementleri)
        subtitles = []
        secici = HTMLHelper(istek.text)
        for track in secici.select("track"):
            raw_src = track.attrs.get("src") or ""
            raw_src = raw_src.strip()
            label   = track.attrs.get("label") or track.attrs.get("srclang") or "Altyazı"
            
            if raw_src:
                full_url = raw_src if raw_src.startswith("http") else f"{self.main_url}{raw_src}"
                subtitles.append(Subtitle(name=label, url=full_url))

        return ExtractResult(
            name      = self.name,
            url       = m3u_link,
            referer   = self.main_url,
            subtitles = subtitles
        )
