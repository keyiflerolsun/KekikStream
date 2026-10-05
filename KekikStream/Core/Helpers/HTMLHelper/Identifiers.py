# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.


"""HTML identifiers işlemleri."""

import re

_RE_IMDB_URL = re.compile(r"imdb\.com/title/(tt\d+)", re.I)
_RE_IMDB_ID  = re.compile(r"\b(tt\d{6,10})\b", re.I)
_RE_TMDB_URL = re.compile(r"(?:themoviedb\.org/(?:3/)?(?:movie|tv)/|tmdb(?:id)?[:/=_])(\d+)", re.I)
_RE_TMDB_ID  = re.compile(r'''\b(?:tmdb(?:_id|id)?|tmdb:id)["']?\s*[:=]\s*["']?(\d+)\b''', re.I)


def extract_imdb_id_text(text):
    match = _RE_IMDB_URL.search(text or "") or _RE_IMDB_ID.search(text or "")
    return match.group(1) if match else None


def extract_tmdb_id_text(text):
    match = _RE_TMDB_URL.search(text or "") or _RE_TMDB_ID.search(text or "")
    return match.group(1) if match else None


class HTMLIdentifiersMixin:
    def extract_imdb_id(self, *selectors: str, target_text: str | None = None) -> str | None:
        """
        HTML veya belirtilen selector / metin içinden IMDB ID'sini (tt1234567) ayıklar.
        Örnekler: "https://www.imdb.com/title/tt0137523/", "tt0137523" -> "tt0137523"
        """
        if target_text:
            if m := _RE_IMDB_URL.search(target_text):
                return m.group(1)
            if m := _RE_IMDB_ID.search(target_text):
                return m.group(1)

        for sel in selectors:
            el = self.select_first(sel)
            if not el:
                continue
            # Attribute'ları kontrol et
            for attr in ("href", "data-imdb", "data-id", "data-imdb-id", "content"):
                if val := el.attrs.get(attr):
                    if m := _RE_IMDB_URL.search(val):
                        return m.group(1)
                    if m := _RE_IMDB_ID.search(val):
                        return m.group(1)
            # Text içeriğini kontrol et
            txt = el.text(strip=True)
            if m := _RE_IMDB_URL.search(txt):
                return m.group(1)
            if m := _RE_IMDB_ID.search(txt):
                return m.group(1)

        # Fallback 1: Sayfadaki linkler (a[href*='imdb.com/title/'])
        if href := self.select_attr("a[href*='imdb.com/title/']", "href"):
            if m := _RE_IMDB_URL.search(href):
                return m.group(1)

        # Fallback 2: Meta etiketleri
        for meta_name in ("imdb:id", "imdb", "pageId", "twitter:data1"):
            if val := self.meta_tag(meta_name):
                if m := _RE_IMDB_ID.search(val):
                    return m.group(1)

        # Fallback 3: Düz HTML regex araması
        return extract_imdb_id_text(self.html)

    @property
    def imdb_id(self) -> str | None:
        """HTML belgesi içindeki ilk geçerli IMDB ID'sini (tt1234567) döner."""
        return self.extract_imdb_id()

    def extract_tmdb_id(self, *selectors: str, target_text: str | None = None) -> str | None:
        """
        HTML veya belirtilen selector / metin içinden TMDB ID'sini ayıklar.
        Örnekler: "https://www.themoviedb.org/movie/550", "tmdb/1399" -> "550", "1399"
        """
        if target_text:
            if value := extract_tmdb_id_text(target_text):
                return value

        for sel in selectors:
            el = self.select_first(sel)
            if not el:
                continue
            for attr in ("href", "data-tmdb", "data-id", "data-tmdb-id", "content"):
                if val := el.attrs.get(attr):
                    if value := extract_tmdb_id_text(val):
                        return value
                    if val.isdigit():
                        return val
            txt = el.text(strip=True)
            if value := extract_tmdb_id_text(txt):
                return value

        # Fallback 1: Sayfadaki linkler
        if href := self.select_attr("a[href*='themoviedb.org/']", "href"):
            if m := _RE_TMDB_URL.search(href):
                return m.group(1)

        # Meta etiketlerinde kimlik tek başına bulunabilir.
        for meta_name in ("tmdb:id", "tmdb", "tmdb_id"):
            if value := self.meta_tag(meta_name):
                if value.isdigit():
                    return value

        return extract_tmdb_id_text(self.html)

    @property
    def tmdb_id(self) -> str | None:
        """HTML belgesi içindeki ilk geçerli TMDB ID'sini döner."""
        return self.extract_tmdb_id()
