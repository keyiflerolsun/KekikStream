# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.


"""HTML helper işlemleri."""

from selectolax.lexbor import LexborHTMLParser, LexborNode
from .Nodes            import _SelectorMixin, NodeHelper
from .Metadata         import HTMLMetadataMixin
from .Cards            import HTMLCardsMixin
from .Labels           import HTMLLabelsMixin
from .Media            import HTMLMediaMixin
from .Identifiers      import HTMLIdentifiersMixin
from ..TextHelper      import TextHelper
import json


class HTMLHelper(_SelectorMixin, HTMLMetadataMixin, HTMLCardsMixin, HTMLLabelsMixin, HTMLMediaMixin, HTMLIdentifiersMixin, TextHelper):
    """Tek HTML belgesinin seçici, metin ve metadata işlemlerini birleştirir."""

    def __init__(self, html: str):
        self.html   = html or ""
        self.parser = LexborHTMLParser(self.html)

    def select(self, selector: str) -> list[NodeHelper]:
        """CSS selector ile tüm eşleşen elementleri döndür."""
        return [NodeHelper(node) for node in self._raw_all(selector)]

    def select_first(self, selector: str | None) -> NodeHelper | None:
        """CSS selector ile ilk eşleşen elementi döndür."""
        node = self._raw_first(selector)
        return NodeHelper(node) if node else None

    def _raw_first(self, selector: str | None) -> LexborNode | None:
        return self.parser.css_first(selector) if selector else None

    def _raw_all(self, selector: str) -> list[LexborNode]:
        return self.parser.css(selector)

    def select_json(self, selector: str | None = None) -> dict | list | None:
        """Belirtilen selector altındaki (örn: script#__NEXT_DATA__) JSON metnini parse eder."""
        txt = self.select_text(selector) if selector else self.html
        if not txt:
            return None
        try:
            return json.loads(txt)
        except Exception:
            return None
