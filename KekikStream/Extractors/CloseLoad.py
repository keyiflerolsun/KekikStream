# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import ExtractorBase, ExtractResult, Subtitle
from Kekik.Sifreleme   import Packer, StreamDecoder
from selectolax.parser import HTMLParser
import re, json

class CloseLoadExtractor(ExtractorBase):
    name     = "CloseLoad"
    main_url = "https://closeload.filmmakinesi.to"

    def _extract_from_json_ld(self, html: str) -> str | None:
        """JSON-LD script tag'inden contentUrl'i çıkar (Kotlin versiyonundaki gibi)"""
        secici = HTMLParser(html)
        for script in secici.css("script[type='application/ld+json']"):
            try:
                data = json.loads(script.text(strip=True))
                if content_url := data.get("contentUrl"):
                    if content_url.startswith("http"):
                        return content_url
            except (json.JSONDecodeError, TypeError):
                # Regex ile contentUrl'i çıkarmayı dene
                match = re.search(r'"contentUrl"\s*:\s*"([^"]+)"', script.text())
                if match and match.group(1).startswith("http"):
                    return match.group(1)
        return None

    def _extract_from_packed(self, html: str) -> str | None:
        """Packed JavaScript'ten video URL'sini çıkar (fallback)"""
        try:
            eval_func = re.compile(r'\s*(eval\(function[\s\S].*)').findall(html)
            if eval_func:
                return StreamDecoder.extract_stream_url(Packer.unpack(eval_func[0]))
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
        secici = HTMLParser(istek.text)
        for track in secici.css("track"):
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
