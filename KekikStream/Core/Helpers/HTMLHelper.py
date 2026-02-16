# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from __future__ import annotations

from selectolax.parser import HTMLParser, Node
import html as _html
import re


class NodeHelper:
    """
    selectolax.Node wrapper — HTMLHelper'ın seçici metotlarını element seviyesinde kullanım için sağlar.

    Kullanım:
        for veri in secici.select("li.film"):
            title  = veri.select_text("span.film-title")
            url    = veri.select_attr("a", "href")
            poster = veri.select_poster("img")
    """

    __slots__ = ("_node",)

    def __init__(self, node: Node):
        self._node = node

    def __getattr__(self, name):
        """Tanımsız attribute erişimlerini alttaki Node'a proxy eder."""
        return getattr(self._node, name)

    def __bool__(self):
        return self._node is not None

    def __repr__(self):
        return f"NodeHelper(<{self._node.tag}>)" if self._node else "NodeHelper(None)"

    # -- Temel Node proxy'leri --

    @property
    def attrs(self) -> dict:
        return self._node.attrs

    @property
    def tag(self) -> str:
        return self._node.tag

    @property
    def parent(self) -> NodeHelper | None:
        p = self._node.parent
        return NodeHelper(p) if p else None

    @property
    def next(self) -> NodeHelper | None:
        n = self._node.next
        return NodeHelper(n) if n else None

    def text(self, *args, **kwargs) -> str:
        return self._node.text(*args, **kwargs)

    # -- CSS seçici metotları (HTMLHelper-uyumlu) --

    def select(self, selector: str) -> list[NodeHelper]:
        """CSS selector ile tüm eşleşen child elementleri döndür."""
        return [NodeHelper(n) for n in self._node.css(selector)]

    def select_first(self, selector: str | None = None) -> NodeHelper | None:
        """CSS selector ile ilk eşleşen child elementi döndür."""
        if not selector:
            return self
        result = self._node.css_first(selector)
        return NodeHelper(result) if result else None

    def select_text(self, selector: str | None = None) -> str:
        """CSS selector ile element bul ve text içeriğini döndür."""
        el = self._node.css_first(selector) if selector else self._node
        if not el:
            return ""
        val = el.text(strip=True)
        return _html.unescape(val) if val else ""

    def select_texts(self, selector: str) -> list[str]:
        """CSS selector ile tüm eşleşen elementlerin text içeriklerini döndür."""
        return [_html.unescape(t) for el in self._node.css(selector) if (t := el.text(strip=True))]

    def select_attr(self, selector: str | None, attr: str) -> str | None:
        """CSS selector ile element bul ve attribute değerini döndür."""
        el = self._node.css_first(selector) if selector else self._node
        return el.attrs.get(attr) if el else None

    def select_attrs(self, selector: str, attr: str) -> list[str]:
        """CSS selector ile tüm eşleşen elementlerin attribute değerlerini döndür."""
        return [v for el in self._node.css(selector) if (v := el.attrs.get(attr))]

    def select_poster(self, selector: str = "img") -> str | None:
        """Poster URL'sini çıkar. Önce data-src, sonra src dener."""
        el = self._node.css_first(selector) if selector else self._node
        if not el:
            return None
        return el.attrs.get("data-src") or el.attrs.get("src")

    def select_direct_text(self, selector: str | None = None) -> str | None:
        """Elementin yalnızca kendi düz metnini döndürür."""
        el = self._node.css_first(selector) if selector else self._node
        if not el:
            return None
        val = el.text(strip=True, deep=False)
        return val or None


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

    def select(self, selector: str) -> list[NodeHelper]:
        """CSS selector ile tüm eşleşen elementleri döndür."""
        return [NodeHelper(n) for n in self.parser.css(selector)]

    def select_first(self, selector: str | None) -> NodeHelper | None:
        """CSS selector ile ilk eşleşen elementi döndür."""
        if not selector:
            return None
        result = self.parser.css_first(selector)
        return NodeHelper(result) if result else None

    def select_text(self, selector: str | None = None) -> str:
        """CSS selector ile element bul ve text içeriğini döndür."""
        el = self.select_first(selector)
        if not el:
            return ""
        val = el.text(strip=True)
        return _html.unescape(val) if val else ""

    def select_texts(self, selector: str) -> list[str]:
        """CSS selector ile tüm eşleşen elementlerin text içeriklerini döndür."""
        return [_html.unescape(t) for el in self.select(selector) if (t := el.text(strip=True))]

    def select_attr(self, selector: str | None, attr: str) -> str | None:
        """CSS selector ile element bul ve attribute değerini döndür."""
        el = self.select_first(selector)
        return el.attrs.get(attr) if el else None

    def select_attrs(self, selector: str, attr: str) -> list[str]:
        """CSS selector ile tüm eşleşen elementlerin attribute değerlerini döndür."""
        return [v for el in self.select(selector) if (v := el.attrs.get(attr))]

    def select_poster(self, selector: str = "img") -> str | None:
        """Poster URL'sini çıkar. Önce data-src, sonra src dener."""
        el = self.select_first(selector)
        if not el:
            return None
        return el.attrs.get("data-src") or el.attrs.get("src")

    def select_direct_text(self, selector: str | None = None) -> str | None:
        """Elementin yalnızca kendi düz metnini döndürür (child elementlerin text'ini katmadan)."""
        el = self.select_first(selector)
        if not el:
            return None
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
        if container_selector:
            targets = self.select(container_selector)
        else:
            body = self.parser.body
            targets = [NodeHelper(body)] if body else []

        for root in targets:
            if not root:
                continue

            # Label belirtebilecek elementleri tara
            for label_el in root.select("span, strong, b, label, dt, div.f-info-label, div.fi-label"):
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

        if container_selector:
            targets = self.select(container_selector)
        else:
            body = self.parser.body
            targets = [NodeHelper(body)] if body else []

        for root in targets:
            if not root:
                continue
            for label_el in root.select("span, strong, b, label, dt, div.f-info-label, div.fi-label"):
                if needle in (label_el.text(strip=True) or "").casefold():
                    # Eğer elementin ebeveyninde linkler varsa (Kutucuklu yapı), onları al
                    parent = label_el.parent
                    links  = parent.select_texts("a") if parent else []
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

    def regex_first(self, pattern: str, target: str | int | None = None, group: int | None = 1, flags: int = 0) -> str | tuple | None:
        """Regex ile arama yap, istenen grubu döndür (group=None ise tüm grupları tuple olarak döndür)."""
        match = re.search(pattern, self._regex_source(target), flags=flags)
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

    def extract_year(self, *selectors: str, pattern: str = r"(?<!\&#)\b(19\d{2}|20\d{2})\b") -> int | None:
        """
        Birden fazla selector veya regex ile 1900-2099 arası bir yıl bilgisini çıkarır.
        HTML entity'leri (&#8211; gibi) yakalamamak için negatif lookbehind kullanır.
        """
        for selector in selectors:
            if text := self.select_text(selector):
                if m := re.search(r"\b(19\d{2}|20\d{2})\b", text):
                    return int(m.group(1))

        # Eğer hala bulunamadıysa regex ile dökümanda ara (sadece selector ile belirtilmediyse veya bulunamadıysa)
        val = self.regex_first(pattern)
        return int(val) if val and str(val).isdigit() else None

    def extract_duration(self, label: str = "Süre", container_selector: str | None = None) -> int | None:
        """Süreyi (dakika olarak) meta verilerden veya metinden çıkar."""
        raw = self.meta_value(label, container_selector)
        if not raw:
            # Düz metinde "91 dakika" gibi ara
            raw = self.regex_first(r"(\d+)\s*(?:dakika|dk|min|m)", self.html)
            if not raw:
                return None

        # Sayıları ayıkla
        nums = re.findall(r"(\d+)", str(raw))
        if not nums:
            return None

        # Genellikle ilk sayı yeterlidir (örn: "90 dk" -> 90)
        return int(nums[0])
