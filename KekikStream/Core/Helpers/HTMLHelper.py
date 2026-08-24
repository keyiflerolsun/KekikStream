# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from __future__ import annotations

from selectolax.parser import HTMLParser, Node
import html as _html
import re, json

# Modül seviyesinde derlenmiş regex sabitleri (her çağrıda yeniden derlenmez)
_RE_SE            = re.compile(r"[Ss](\d+)[Ee](\d+)")
_RE_SEASON        = re.compile(r"(\d+)\.\s*[Ss]ezon|[Ss]ezon[- ]?(\d+)|[Ss]eason[- ]?(\d+)|-(\d+)-sezon|S(\d+)|(\d+)\.[Ss]", re.I)
_RE_EPISODE       = re.compile(r"(\d+)\.\s*[Bb][\u00f6o]l[\u00fcu]m|[Bb][\u00f6o]l[\u00fcu]m[- ]?(\d+)|[Ee]pisode[- ]?(\d+)|[Ee]ps[- ]?(\d+)|-(\d+)-bolum|[Ee](\d+)", re.I)
_RE_YEAR_SIMPLE   = re.compile(r"\b(19\d{2}|20\d{2})\b")
_RE_DURATION_NUMS = re.compile(r"(\d+)")
_RE_RATING        = re.compile(r"(?:imdb|tmdb|puan|score|rating)?\s*[:/]?\s*(\d{1,2}(?:[\.,]\d{1,2})?)\s*(?:/\s*10)?", re.I)
_RE_PLAYERJS_SUB  = re.compile(r"\[([^\]]+)\](https?://[^\s,\"\']+)")
_RE_IMDB_URL      = re.compile(r"imdb\.com/title/(tt\d+)", re.I)
_RE_IMDB_ID       = re.compile(r"\b(tt\d{6,10})\b", re.I)
_RE_TMDB_URL      = re.compile(r"(?:themoviedb\.org/(?:3/)?(?:movie|tv)/|tmdb(?:id)?[:/=_])(\d+)", re.I)


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

    @property
    def html(self) -> str:
        """Node'un ham HTML içeriği."""
        return self._node.html or ""

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
        """Poster URL'sini çıkar. Sırasıyla data-src, data-original, data-lazy-src, data-srcset, src dener."""
        el = self._node.css_first(selector) if selector else self._node
        if not el:
            return None
        attrs = el.attrs
        return (
            attrs.get("data-src")
            or attrs.get("data-original")
            or attrs.get("data-lazy-src")
            or attrs.get("data-srcset")
            or attrs.get("src")
        )

    def select_direct_text(self, selector: str | None = None) -> str | None:
        """Elementin yalnızca kendi düz metnini döndürür."""
        el = self._node.css_first(selector) if selector else self._node
        if not el:
            return None
        val = el.text(strip=True, deep=False)
        return val or None

    def select_json(self, selector: str | None = None) -> dict | list | None:
        """Belirtilen selector altındaki JSON metnini parse eder."""
        txt = self.select_text(selector) if selector else self.text(strip=True)
        if not txt:
            return None
        try:
            return json.loads(txt)
        except Exception:
            return None


class HTMLHelper:
    """
    Selectolax ile HTML parsing işlemlerini temiz, kısa ve okunabilir hale getiren yardımcı sınıf.
    """

    def __init__(self, html: str):
        self.html   = html or ""
        self.parser = HTMLParser(self.html)

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
        """Poster URL'sini çıkar. Sırasıyla data-src, data-original, data-lazy-src, data-srcset, src dener."""
        el = self.select_first(selector)
        if not el:
            return None
        attrs = el.attrs
        return (
            attrs.get("data-src")
            or attrs.get("data-original")
            or attrs.get("data-lazy-src")
            or attrs.get("data-srcset")
            or attrs.get("src")
        )

    def select_direct_text(self, selector: str | None = None) -> str | None:
        """Elementin yalnızca kendi düz metnini döndürür (child elementlerin text'ini katmadan)."""
        el = self.select_first(selector)
        if not el:
            return None
        val = el.text(strip=True, deep=False)
        return val or None

    def select_json(self, selector: str | None = None) -> dict | list | None:
        """Belirtilen selector altındaki (örn: script#__NEXT_DATA__) JSON metnini parse eder."""
        txt = self.select_text(selector) if selector else self.html
        if not txt:
            return None
        try:
            return json.loads(txt)
        except Exception:
            return None

    # ========================
    # OPENGRAPH & META İŞLEMLERİ
    # ========================

    def meta_tag(self, name_or_prop: str, attr: str = "content") -> str | None:
        """
        <meta property="..." content="...">, <meta name="..." content="..."> veya
        <meta itemprop="..." content="..."> etiketinden değer okur.
        """
        for sel in (
            f"meta[property='{name_or_prop}']",
            f"meta[name='{name_or_prop}']",
            f"meta[itemprop='{name_or_prop}']",
            f"meta[property=\"{name_or_prop}\"]",
            f"meta[name=\"{name_or_prop}\"]",
        ):
            if val := self.select_attr(sel, attr):
                return _html.unescape(val.strip())
        return None

    @property
    def og_title(self) -> str | None:
        """OpenGraph başlığı veya standart <title> / twitter:title etiketini döndürür."""
        return (
            self.meta_tag("og:title")
            or self.meta_tag("twitter:title")
            or self.meta_tag("title")
            or self.select_text("title")
            or None
        )

    @property
    def og_poster(self) -> str | None:
        """OpenGraph poster URL'si veya twitter:image / image_src etiketini döndürür."""
        return (
            self.meta_tag("og:image")
            or self.meta_tag("og:image:url")
            or self.meta_tag("twitter:image")
            or self.meta_tag("twitter:image:src")
            or self.select_attr("link[rel='image_src']", "href")
            or None
        )

    # og_poster için geriye dönük takma ad (alias)
    og_image = og_poster

    @property
    def og_description(self) -> str | None:
        """OpenGraph açıklaması veya meta description / twitter:description etiketini döndürür."""
        return (
            self.meta_tag("og:description")
            or self.meta_tag("description")
            or self.meta_tag("twitter:description")
            or None
        )

    # ========================
    # TOPLU KART / İÇERİK AYIKLAYICI
    # ========================

    def extract_cards(
        self,
        container   : str,
        title       : str | None            = None,
        url         : str | None            = None,
        poster      : str | None            = "img",
        title_attr  : str | None            = None,
        url_attr    : str                   = "href",
        poster_attr : str | None            = None,
        rating      : str | None            = None,
        extra       : dict[str, str] | None = None,
    ) -> list[dict[str, str | None]]:
        """
        Katalog ve arama sayfalarındaki kart listelerini standartlaştırılmış bir yapıda ayıklar.

        Kullanım:
            veriler = secici.extract_cards(
                container = "div.film-item",
                title     = "h2.title a",
                url       = "h2.title a",
                poster    = "img.poster",
                rating    = "span.imdb"
            )
        """
        cards = []
        for el in self.select(container):
            # 1. Başlık
            if title_attr and title:
                c_title = el.select_attr(title, title_attr)
            elif title:
                c_title = el.select_text(title)
            else:
                c_title = el.select_attr("a", "title") or el.select_text("a") or el.select_text(None)

            # 2. URL
            if url:
                c_url = el.select_attr(url, url_attr)
            else:
                c_url = el.attrs.get(url_attr) if el.tag == "a" else el.select_attr("a", url_attr)

            # 3. Poster
            if poster_attr and poster:
                c_poster = el.select_attr(poster, poster_attr)
            elif poster:
                c_poster = el.select_poster(poster)
            else:
                c_poster = el.select_poster("img")

            # 4. Rating (Opsiyonel)
            c_rating = el.select_text(rating) if rating else None

            card_data = {
                "title"  : c_title.strip() if c_title else None,
                "url"    : c_url.strip() if c_url else None,
                "poster" : c_poster.strip() if c_poster else None,
            }

            if rating:
                card_data["rating"] = c_rating.strip() if c_rating else None

            if extra:
                for k, sel in extra.items():
                    card_data[k] = el.select_text(sel)

            if card_data["title"] or card_data["url"]:
                cards.append(card_data)

        return cards

    # ========================
    # JSON-LD (SCHEMA.ORG) İŞLEMLERİ
    # ========================

    def extract_json_ld(self, schema_type: str | None = None) -> list[dict] | dict | None:
        """
        Sayfadaki <script type="application/ld+json"> bloklarını parse eder.
        schema_type belirtilirse (örn: "Movie", "TVSeries") yalnızca o tipe uyan ilk nesneyi döner.
        """
        all_schemas: list[dict] = []

        for script in self.select("script[type='application/ld+json']"):
            txt = script.text(strip=True)
            if not txt:
                continue
            try:
                data = json.loads(txt)
                if isinstance(data, list):
                    all_schemas.extend([x for x in data if isinstance(x, dict)])
                elif isinstance(data, dict):
                    if "@graph" in data and isinstance(data["@graph"], list):
                        all_schemas.extend([x for x in data["@graph"] if isinstance(x, dict)])
                    else:
                        all_schemas.append(data)
            except Exception:
                continue

        if not schema_type:
            return all_schemas

        target = schema_type.lower()
        for item in all_schemas:
            item_type = str(item.get("@type", "")).lower()
            if target in item_type:
                return item

        return None

    def extract_json_ld_metadata(self) -> dict:
        """
        JSON-LD içindeki Movie/TVSeries şemasından title, description, poster, year, rating gibi alanları ayıklar.
        """
        schema = self.extract_json_ld("Movie") or self.extract_json_ld("TVSeries") or self.extract_json_ld("VideoObject")
        if not schema or not isinstance(schema, dict):
            return {}

        result = {}

        # Title
        if name := schema.get("name"):
            result["title"] = str(name).strip()

        # Description
        if desc := schema.get("description"):
            result["description"] = str(desc).strip()

        # Poster / Image
        img = schema.get("image")
        if isinstance(img, str):
            result["poster"] = img
        elif isinstance(img, dict):
            result["poster"] = img.get("url") or img.get("contentUrl")
        elif isinstance(img, list) and img:
            result["poster"] = img[0] if isinstance(img[0], str) else img[0].get("url")

        # Date / Year
        date_str = schema.get("dateCreated") or schema.get("datePublished") or schema.get("uploadDate")
        if date_str:
            if m := _RE_YEAR_SIMPLE.search(str(date_str)):
                result["year"] = m.group(1)

        # Rating
        rating_obj = schema.get("aggregateRating")
        if isinstance(rating_obj, dict):
            if val := rating_obj.get("ratingValue"):
                result["rating"] = str(val)

        # Actors
        actors = schema.get("actor") or schema.get("actors")
        if isinstance(actors, list):
            names = [a.get("name") if isinstance(a, dict) else str(a) for a in actors]
            result["actors"] = ", ".join([n for n in names if n])

        # Tags / Genre
        genre = schema.get("genre")
        if isinstance(genre, list):
            result["tags"] = ", ".join([str(g) for g in genre if g])
        elif isinstance(genre, str):
            result["tags"] = genre

        return result

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
            body    = self.parser.body
            targets = [NodeHelper(body)] if body else []

        for root in targets:
            if not root:
                continue

            # Label belirtebilecek elementleri tara
            for label_el in root.select("span, strong, b, label, dt, td, div.f-info-label, div.fi-label"):
                # tek .text() çağrısı + tek casefold — raw_txt orijinali, txt normalized
                raw_txt = label_el.text(strip=True) or ""
                txt     = raw_txt.casefold()
                if needle not in txt:
                    continue

                # 1) Elementin kendi içindeki text'te LABEL: VALUE formatı olabilir
                # "Oyuncular: Brad Pitt" gibi. LABEL: sonrasını al.
                if ":" in raw_txt and needle in txt.split(":")[0]:  # txt zaten casefold
                    val = raw_txt.split(":", 1)[1].strip()
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
                    else:  # <br> gördüysek satır bitmiştir
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
            for label_el in root.select("span, strong, b, label, dt, td, div.f-info-label, div.fi-label"):
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

    def regex_all(self, pattern: str, target: str | int | None = None, flags: int = 0) -> list[str] | list[tuple]:
        """Regex ile tüm eşleşmeleri döndür."""
        return re.findall(pattern, self._regex_source(target), flags=flags)

    def regex_replace(self, pattern: str, repl: str, target: str | int | None = None, flags: int = 0) -> str:
        """Regex ile replace yap."""
        return re.sub(pattern, repl, self._regex_source(target), flags=flags)

    # ========================
    # ÖZEL AYIKLAYICILAR
    # ========================

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

    def extract_year(self, *selectors: str, pattern: str = r"(?<!\&#)\b(19\d{2}|20\d{2})\b") -> int | None:
        """
        Birden fazla selector veya regex ile 1900-2099 arası bir yıl bilgisini çıkarır.
        HTML entity'leri (&#8211; gibi) yakalamamak için negatif lookbehind kullanır.
        """
        for selector in selectors:
            if text := self.select_text(selector):
                # Modül seviyesi derlenmiş _RE_YEAR_SIMPLE kullan
                if m := _RE_YEAR_SIMPLE.search(text):
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
        nums = _RE_DURATION_NUMS.findall(str(raw))
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
        Örnek: "[Türkçe]https://site.com/tr.vtt,[English]https://site.com/en.vtt"
        Dönüş: [{"name": "Türkçe", "url": "https://..."}, ...]
        """
        if not text:
            return []
        matches = _RE_PLAYERJS_SUB.findall(text)
        return [{"name": name.strip(), "url": url.strip()} for name, url in matches if url]

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
        if m := _RE_IMDB_URL.search(self.html):
            return m.group(1)

        return None

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
            if m := _RE_TMDB_URL.search(target_text):
                return m.group(1)

        for sel in selectors:
            el = self.select_first(sel)
            if not el:
                continue
            for attr in ("href", "data-tmdb", "data-id", "data-tmdb-id", "content"):
                if val := el.attrs.get(attr):
                    if m := _RE_TMDB_URL.search(val):
                        return m.group(1)
            txt = el.text(strip=True)
            if m := _RE_TMDB_URL.search(txt):
                return m.group(1)

        # Fallback 1: Sayfadaki linkler
        if href := self.select_attr("a[href*='themoviedb.org/']", "href"):
            if m := _RE_TMDB_URL.search(href):
                return m.group(1)

        # Fallback 2: Düz HTML regex araması
        if m := _RE_TMDB_URL.search(self.html):
            return m.group(1)

        return None

    @property
    def tmdb_id(self) -> str | None:
        """HTML belgesi içindeki ilk geçerli TMDB ID'sini döner."""
        return self.extract_tmdb_id()
