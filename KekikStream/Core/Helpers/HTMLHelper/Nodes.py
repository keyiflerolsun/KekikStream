# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.


"""HTML nodes işlemleri."""

from selectolax.lexbor import LexborNode
import html, json

_POSTER_ATTRS = ("data-src", "data-original", "data-lazy-src", "data-srcset", "srcset", "src")


def _optional_text(value: str | None) -> str | None:
    """HTML metnini boş değer üretmeden normalize et."""
    if not value:
        return None
    return html.unescape(value).strip() or None


def _poster_attr(attrs: dict) -> str | None:
    for attr in _POSTER_ATTRS:
        if value := _optional_text(attrs.get(attr)):
            if attr in ("data-srcset", "srcset"):
                value = value.split(",", 1)[0].split()[0]
            return value
    return None


class _SelectorMixin:
    """``NodeHelper`` ve ``HTMLHelper``ın ortak, boş-değer güvenli seçici API'si."""

    def _raw_first(self, selector: str | None) -> LexborNode | None:
        raise NotImplementedError

    def _raw_all(self, selector: str) -> list[LexborNode]:
        raise NotImplementedError

    def select_text(self, selector: str | None = None) -> str | None:
        """Anlamlı ilk metni; seçici/alan yoksa ``None`` döndür."""
        node = self._raw_first(selector)
        return _optional_text(node.text(strip=True)) if node else None

    def require_text(self, selector: str | None = None, field: str = "Metin") -> str:
        """Zorunlu metni döndür; yoksa seçiciyi içeren açık bir hata üret."""
        if value := self.select_text(selector):
            return value
        raise ValueError(f"{field} bulunamadı: {selector or 'mevcut düğüm'}")

    def select_texts(self, selector: str) -> list[str]:
        """Anlamlı metni olan tüm eşleşmeleri döndür."""
        return [text for node in self._raw_all(selector) if (text := _optional_text(node.text(strip=True)))]

    def select_attr(self, selector: str | None, attr: str) -> str | None:
        """Anlamlı ilk attribute değerini; yoksa ``None`` döndür."""
        node = self._raw_first(selector)
        return _optional_text(node.attrs.get(attr)) if node else None

    def select_attrs(self, selector: str, attr: str) -> list[str]:
        """Anlamlı attribute değerlerini döndür."""
        return [value for node in self._raw_all(selector) if (value := _optional_text(node.attrs.get(attr)))]

    def select_poster(self, selector: str = "img") -> str | None:
        """Poster için lazy-load attribute zincirini uygula."""
        node = self._raw_first(selector)
        return _poster_attr(node.attrs) if node else None

    def select_direct_text(self, selector: str | None = None) -> str | None:
        """Child elementleri katmadan anlamlı düz metni döndür."""
        node = self._raw_first(selector)
        return _optional_text(node.text(strip=True, deep=False)) if node else None


class NodeHelper(_SelectorMixin):
    """
    selectolax.lexbor.LexborNode wrapper — HTMLHelper'ın seçici metotlarını element seviyesinde kullanım için sağlar.

    Kullanım:
        for veri in secici.select("li.film"):
            title  = veri.select_text("span.film-title")
            url    = veri.select_attr("a", "href")
            poster = veri.select_poster("img")
    """

    __slots__ = ("_node",)

    def __init__(self, node: LexborNode):
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
    def parent(self) -> "NodeHelper | None":
        p = self._node.parent
        return NodeHelper(p) if p else None

    @property
    def next(self) -> "NodeHelper | None":
        n = self._node.next
        return NodeHelper(n) if n else None

    def text(self, *args, **kwargs) -> str:
        return self._node.text(*args, **kwargs)

    @property
    def html(self) -> str:
        """Node'un ham HTML içeriği."""
        return self._node.html or ""

    # -- CSS seçici metotları (HTMLHelper-uyumlu) --

    def select(self, selector: str) -> "list[NodeHelper]":
        """CSS selector ile tüm eşleşen child elementleri döndür."""
        return [NodeHelper(node) for node in self._raw_all(selector)]

    def select_first(self, selector: str | None = None) -> "NodeHelper | None":
        """CSS selector ile ilk eşleşen child elementi döndür."""
        node = self._raw_first(selector)
        return NodeHelper(node) if node else None

    def _raw_first(self, selector: str | None) -> LexborNode | None:
        return self._node.css_first(selector) if selector else self._node

    def _raw_all(self, selector: str) -> list[LexborNode]:
        return self._node.css(selector)

    def select_json(self, selector: str | None = None) -> dict | list | None:
        """Belirtilen selector altındaki JSON metnini parse eder."""
        txt = self.select_text(selector) if selector else self.text(strip=True)
        if not txt:
            return None
        try:
            return json.loads(txt)
        except Exception:
            return None
