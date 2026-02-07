# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from __future__ import annotations

import re
from selectolax.parser import HTMLParser, Node


class HTMLHelper:
    """
    Selectolax ile HTML parsing işlemlerini temiz, kısa ve okunabilir hale getiren yardımcı sınıf.
    """

    def __init__(self, html: str):
        self.html   = html
        self.parser = HTMLParser(html)

    # ========================
    # SELECTOR (CSS) İŞLEMLERİ
    # ========================

    def _root(self, element: Node | None) -> Node | HTMLParser:
        """İşlem yapılacak temel elementi döndürür."""
        return element if element is not None else self.parser

    def select(self, selector: str, element: Node | None = None) -> list[Node]:
        """CSS selector ile tüm eşleşen elementleri döndür."""
        return self._root(element).css(selector)

    def select_first(self, selector: str | None, element: Node | None = None) -> Node | None:
        """CSS selector ile ilk eşleşen elementi döndür."""
        if not selector:
            return element
        return self._root(element).css_first(selector)

    def select_text(self, selector: str | None = None, element: Node | None = None) -> str | None:
        """CSS selector ile element bul ve text içeriğini döndür."""
        el = self.select_first(selector, element)
        if not el:
            return None
        val = el.text(strip=True)
        return val or None

    def select_texts(self, selector: str, element: Node | None = None) -> list[str] | None:
        """CSS selector ile tüm eşleşen elementlerin text içeriklerini döndür."""
        out: list[str] = []
        for el in self.select(selector, element):
            txt = el.text(strip=True)
            if txt:
                out.append(txt)
        return out or None

    def select_attr(self, selector: str | None, attr: str, element: Node | None = None) -> str | None:
        """CSS selector ile element bul ve attribute değerini döndür."""
        el = self.select_first(selector, element)
        return el.attrs.get(attr) if el else None

    def select_attrs(self, selector: str, attr: str, element: Node | None = None) -> list[str]:
        """CSS selector ile tüm eşleşen elementlerin attribute değerlerini döndür."""
        out: list[str] = []
        for el in self.select(selector, element):
            val = el.attrs.get(attr)
            if val:
                out.append(val)
        return out

    def select_poster(self, selector: str = "img", element: Node | None = None) -> str | None:
        """Poster URL'sini çıkar. Önce data-src, sonra src dener."""
        el = self.select_first(selector, element)
        if not el:
            return None
        return el.attrs.get("data-src") or el.attrs.get("src")

    def select_direct_text(self, selector: str, element: Node | None = None) -> str | None:
        """
        Elementin yalnızca "kendi" düz metnini döndürür (child elementlerin text'ini katmadan).
        """
        el = self.select_first(selector, element)
        if not el:
            return None

        # type: ignore[call-arg]
        val = el.text(strip=True, deep=False)
        return val or None

    # ========================
    # META (LABEL -> VALUE) İŞLEMLERİ
    # ========================

    def meta_value(self, label: str, container_selector: str | None = None) -> str | None:
        """
        Herhangi bir container içinde: LABEL metnini içeren bir elementten SONRA gelen metni döndürür.
        label örn: "Oyuncular", "Yapım Yılı", "IMDB"
        """
        needle = label.casefold()

        # Belirli bir container varsa içinde ara, yoksa tüm dökümanda
        targets = self.select(container_selector) if container_selector else [self.parser.body]

        for root in targets:
            if not root:
                continue

            # Kalın/vurgulu elementlerde (span, strong, b, label, dt) label'ı ara
            for label_el in self.select("span, strong, b, label, dt", root):
                txt = (label_el.text(strip=True) or "").casefold()
                if needle not in txt:
                    continue

                # 1) Elementin kendi içindeki text'te LABEL: VALUE formatı olabilir
                # "Oyuncular: Brad Pitt" gibi. LABEL: sonrasını al.
                full_txt = label_el.text(strip=True)
                if ":" in full_txt and needle in full_txt.split(":")[0].casefold():
                    val = full_txt.split(":", 1)[1].strip()
                    if val:
                        return val

                # 2) Label sonrası gelen ilk text node'u veya element'i al
                curr = label_el.next
                while curr:
                    if curr.tag == "-text":
                        val = curr.text(strip=True).strip(" :")
                        if val:
                            return val
                    elif curr.tag != "br":
                        val = curr.text(strip=True).strip(" :")
                        if val:
                            return val
                    else: # <br> gördüysek satır bitmiştir
                        break
                    curr = curr.next

        return None

    def meta_list(self, label: str, container_selector: str | None = None, sep: str = ",") -> list[str]:
        """meta_value(...) çıktısını veya label'ın ebeveynindeki linkleri listeye döndürür."""
        needle = label.casefold()
        targets = self.select(container_selector) if container_selector else [self.parser.body]

        for root in targets:
            if not root:
                continue
            for label_el in self.select("span, strong, b, label, dt", root):
                if needle in (label_el.text(strip=True) or "").casefold():
                    # Eğer elementin ebeveyninde linkler varsa (Kutucuklu yapı), onları al
                    links = self.select_texts("a", label_el.parent)
                    if links:
                        return links

                    # Yoksa düz metin olarak meta_value mantığıyla al
                    raw = self.meta_value(label, container_selector=container_selector)
                    if not raw:
                        return []
                    return [x.strip() for x in raw.split(sep) if x.strip()]

        return []

    # ========================
    # REGEX İŞLEMLERİ
    # ========================

    def _regex_source(self, target: str | int | None) -> str:
        """Regex için kaynak metni döndürür."""
        return target if isinstance(target, str) else self.html

    def regex_first(self, pattern: str, target: str | int | None = None, group: int | None = 1) -> str | tuple | None:
        """Regex ile arama yap, istenen grubu döndür (group=None ise tüm grupları tuple olarak döndür)."""
        match = re.search(pattern, self._regex_source(target))
        if not match:
            return None

        if group is None:
            return match.groups()

        last_idx = match.lastindex or 0
        return match.group(group) if last_idx >= group else match.group(0)

    def regex_all(self, pattern: str, target: str | int | None = None) -> list[str] | list[tuple]:
        """Regex ile tüm eşleşmeleri döndür."""
        return re.findall(pattern, self._regex_source(target))

    def regex_replace(self, pattern: str, repl: str, target: str | int | None = None) -> str:
        """Regex ile replace yap."""
        return re.sub(pattern, repl, self._regex_source(target))

    # ========================
    # ÖZEL AYIKLAYICILAR
    # ========================

    @staticmethod
    def extract_season_episode(text: str) -> tuple[int | None, int | None]:
        """Metin içinden sezon ve bölüm numarasını çıkar."""
        if m := re.search(r"[Ss](\d+)[Ee](\d+)", text):
            return int(m.group(1)), int(m.group(2))

        s = re.search(r"(\d+)\.\s*[Ss]ezon|[Ss]ezon[- ]?(\d+)|-(\d+)-sezon|S(\d+)|(\d+)\.[Ss]", text, re.I)
        e = re.search(r"(\d+)\.\s*[Bb][öo]l[üu]m|[Bb][öo]l[üu]m[- ]?(\d+)|-(\d+)-bolum|[Ee](\d+)", text, re.I)

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
