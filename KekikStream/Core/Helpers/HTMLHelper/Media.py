# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.


"""HTML media işlemleri."""

from ..TextHelper import extract_year_text, YEAR_PATTERN
from .Duration    import iso8601_duration_minutes
import re

_RE_SE            = re.compile(r"[Ss](\d+)[Ee](\d+)")
_RE_SEASON        = re.compile(r"(\d+)\.\s*[Ss]ezon|[Ss]ezon[- ]?(\d+)|[Ss]eason[- ]?(\d+)|-(\d+)-sezon|S(\d+)|(\d+)\.[Ss]", re.I)
_RE_EPISODE       = re.compile(r"(\d+)\.\s*[Bb][\u00f6o]l[\u00fcu]m|[Bb][\u00f6o]l[\u00fcu]m[- ]?(\d+)|[Ee]pisode[- ]?(\d+)|[Ee]ps[- ]?(\d+)|-(\d+)-bolum|[Ee](\d+)", re.I)
_RE_YEAR_SIMPLE   = re.compile(r"\b(19\d{2}|20\d{2})\b")
_RE_DURATION_NUMS = re.compile(r"(\d+)")
_RE_RATING        = re.compile(r"(?:imdb|tmdb|puan|score|rating)?\s*[:/]?\s*(\d{1,2}(?:[\.,]\d{1,2})?)\s*(?:/\s*10)?", re.I)
_RE_PLAYERJS_SUB  = re.compile(r"\[([^\]]+)\](https?://[^\s,\"\']+)")


class HTMLMediaMixin:
    @staticmethod
    def extract_season_episode(text: str) -> tuple[int | None, int | None]:
        """Metin içinden sezon ve bölüm numarasını çıkar."""
        # Modül seviyesi derlenmiş regex kullan
        if m := _RE_SE.search(text):
            return int(m.group(1)), int(m.group(2))

        s = _RE_SEASON.search(text)
        e = _RE_EPISODE.search(text)

        s_val = next((int(g) for g in s.groups() if g), None) if s else None
        e_val = next((int(g) for g in e.groups() if g), None) if e else None

        return s_val, e_val

    @staticmethod
    def clean_episode_title(text: str) -> str:
        """Episode başlığından 'Eps 1: ' gibi kalıpları temizler."""
        # Sezon/Bölüm belirteçlerini ve sonrasındaki ayraçları temizle
        cleaned = _RE_SE.sub("", text)
        cleaned = _RE_SEASON.sub("", cleaned)
        cleaned = _RE_EPISODE.sub("", cleaned)

        # Başta kalan ayraç ve boşlukları temizle
        return cleaned.strip(" :-").strip()

    def extract_year(self, *selectors: str, pattern: str = YEAR_PATTERN, target_text: object = None) -> int | None:
        """
        Birden fazla selector veya regex ile 1900-2099 arası bir yıl bilgisini çıkarır.
        HTML entity'leri (&#8211; gibi) yakalamamak için negatif lookbehind kullanır.
        """
        if target_text is not None:
            return extract_year_text(target_text, pattern)

        for selector in selectors:
            if text := self.select_text(selector):
                # Modül seviyesi derlenmiş _RE_YEAR_SIMPLE kullan
                if m := _RE_YEAR_SIMPLE.search(text):
                    return int(m.group(1))

        # Eğer hala bulunamadıysa regex ile dökümanda ara (sadece selector ile belirtilmediyse veya bulunamadıysa)
        val = self.regex_first(pattern)
        return int(val) if val and str(val).isdigit() else None

    def extract_duration(self, label: str = "Süre", container_selector: str | None = None, target_text: str | None = None) -> int | None:
        """Süreyi (dakika olarak) meta verilerden veya metinden çıkar."""
        raw = target_text if target_text is not None else self.meta_value(label, container_selector)
        if target_text is None and not raw:
            # Düz metinde "91 dakika" gibi ara
            raw = self.regex_first(r"(\d+)\s*(?:dakika|dk|min|m)", self.html)
            if not raw:
                return None

        # Sayıları ayıkla
        if duration := iso8601_duration_minutes(raw):
            return duration
        nums = _RE_DURATION_NUMS.findall(str(raw or ""))
        if not nums:
            return None

        # Genellikle ilk sayı yeterlidir (örn: "90 dk" -> 90)
        return int(nums[0])

    def extract_rating(self, *selectors: str, target_text: str | None = None) -> str | None:
        """
        Belirtilen selector veya metin içinden IMDB / TMDB puanını ayıklar.
        Örnekler: "IMDB: 8.4", "7.5/10", "Puan: 8,1", "8.0" -> "8.4", "7.5", "8.1", "8.0"
        """
        candidates = []
        for sel in selectors:
            if val := self.select_text(sel):
                candidates.append(val)

        if target_text:
            candidates.append(target_text)

        if not candidates:
            # Fallback: dökümanda genel rating ara
            if val := self.meta_value("IMDB") or self.meta_value("Puan") or self.meta_value("Score"):
                candidates.append(val)

        for txt in candidates:
            if m := _RE_RATING.search(txt):
                raw_score = m.group(1).replace(",", ".")
                try:
                    score_f = float(raw_score)
                    if 0.0 < score_f <= 10.0:
                        return f"{score_f:.1f}" if "." in raw_score else str(int(score_f))
                except ValueError:
                    pass

        return None

    @staticmethod
    def extract_playerjs_subtitles(text: str) -> list[dict[str, str]]:
        """
        PlayerJS formatındaki altyazı dizgesini ayıklar.
        Örnek : "[Türkçe]https://site.com/tr.vtt,[English]https://site.com/en.vtt"
        Dönüş : [{"name" : "Türkçe", "url" : "https://..."}, ...]
        """
        if not text:
            return []
        matches = _RE_PLAYERJS_SUB.findall(text)
        return [{"name" : name.strip(), "url" : url.strip()} for name, url in matches if url]
