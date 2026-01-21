# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from selectolax.parser import HTMLParser, Node
import re


class HTMLHelper:
    """
    Selectolax ile HTML parsing işlemlerini temiz, kısa ve okunabilir hale getiren yardımcı sınıf.
    """

    def __init__(self, html: str):
        self.parser = HTMLParser(html)
        self.html   = html

    # ========================
    # TEMEL SELECTOR İŞLEMLERİ
    # ========================

    def _target(self, element: Node | None) -> Node | HTMLParser:
        """İşlem yapılacak temel elementi döndürür."""
        return element if element is not None else self.parser

    def select(self, selector: str, element: Node | None = None) -> list[Node]:
        """CSS selector ile tüm eşleşen elementleri döndür."""
        return self._target(element).css(selector)

    def select_first(self, selector: str | None, element: Node | None = None) -> Node | None:
        """CSS selector ile ilk eşleşen elementi döndür."""
        if not selector:
            return element

        return self._target(element).css_first(selector)

    def select_text(self, selector: str | None = None, element: Node | None = None, strip: bool = True) -> str | None:
        """CSS selector ile element bul ve text içeriğini döndür."""
        el = self.select_first(selector, element)
        if not el:
            return None

        val = el.text(strip=strip)
        return val if val else None

    def select_attr(self, selector: str | None, attr: str, element: Node | None = None) -> str | None:
        """CSS selector ile element bul ve attribute değerini döndür."""
        el = self.select_first(selector, element)
        return el.attrs.get(attr) if el else None

    def select_all_text(self, selector: str, element: Node | None = None, strip: bool = True) -> list[str]:
        """CSS selector ile tüm eşleşen elementlerin text içeriklerini döndür."""
        return [
            txt for el in self.select(selector, element)
                if (txt := el.text(strip=strip))
        ]

    def select_all_attr(self, selector: str, attr: str, element: Node | None = None) -> list[str]:
        """CSS selector ile tüm eşleşen elementlerin attribute değerlerini döndür."""
        return [
            val for el in self.select(selector, element)
                if (val := el.attrs.get(attr))
        ]

    # ----------------------------------------------

    def select_poster(self, selector: str = "img", element: Node | None = None) -> str | None:
        """Poster URL'sini çıkar. Önce data-src, sonra src dener."""
        el = self.select_first(selector, element)
        if not el:
            return None

        return el.attrs.get("data-src") or el.attrs.get("src")

    # ========================
    # REGEX İŞLEMLERİ
    # ========================

    def _source(self, target: str | int | None) -> str:
        """Regex için kaynak metni döndürür."""
        return target if isinstance(target, str) else self.html

    def _flags(self, target: str | int | None, flags: int) -> int:
        """Regex flags değerini döndürür."""
        return target if isinstance(target, int) else flags

    def regex_first(self, pattern: str, target: str | int | None = None, flags: int = 0) -> str | None:
        """Regex ile arama yap, ilk grubu döndür (grup yoksa tamamını)."""
        match = re.search(pattern, self._source(target), self._flags(target, flags))
        if not match:
            return None

        try:
            return match.group(1)
        except IndexError:
            return match.group(0)

    def regex_all(self, pattern: str, target: str | int | None = None, flags: int = 0) -> list[str]:
        """Regex ile tüm eşleşmeleri döndür."""
        return re.findall(pattern, self._source(target), self._flags(target, flags))

    def regex_replace(self, pattern: str, repl: str, target: str | int | None = None, flags: int = 0) -> str:
        """Regex ile replace yap."""
        return re.sub(pattern, repl, self._source(target), flags)

    # ========================
    # ÖZEL AYIKLAYICILAR
    # ========================

    @staticmethod
    def extract_season_episode(text: str) -> tuple[int | None, int | None]:
        """Metin içinden sezon ve bölüm numarasını çıkar."""
        # S01E05 formatı
        if m := re.search(r"[Ss](\d+)[Ee](\d+)", text):
            return int(m.group(1)), int(m.group(2))

        # Ayrı ayrı ara
        s = re.search(r"(\d+)\.\s*[Ss]ezon|[Ss]ezon[- ]?(\d+)|-(\d+)-sezon|S(\d+)|(\d+)\.[Ss]", text, re.I)
        e = re.search(r"(\d+)\.\s*[Bb][öo]l[üu]m|[Bb][öo]l[üu]m[- ]?(\d+)|-(\d+)-bolum|[Ee](\d+)", text, re.I)

        # İlk bulunan grubu al (None değilse)
        s_val = next((int(g) for g in s.groups() if g), None) if s else None
        e_val = next((int(g) for g in e.groups() if g), None) if e else None

        return s_val, e_val

    def extract_year(self, *selectors: str, pattern: str = r"(\d{4})") -> int | None:
        """Birden fazla selector veya regex ile yıl bilgisini çıkar."""
        for selector in selectors:
            if text := self.select_text(selector):
                if m := re.search(r"(\d{4})", text):
                    return int(m.group(1))

        val = self.regex_first(pattern)
        return int(val) if val and val.isdigit() else None

