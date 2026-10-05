# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.


"""HTML metadata işlemleri."""

from .Duration import json_ld_duration_minutes
import html, re, json

_RE_YEAR_SIMPLE   = re.compile(r"\b(19\d{2}|20\d{2})\b")


def json_ld_rating_value(schema):
    """JSON-LD içindeki gerçek 10 üzerinden medya puanını oku."""
    rating = schema.get("aggregateRating") if isinstance(schema, dict) else None
    if not isinstance(rating, dict):
        return None
    try:
        score = float(str(rating.get("ratingValue")).replace(",", "."))
        best  = float(rating.get("bestRating") or 10)
        if best != 10 or not 0 < score <= 10:
            return None
        return str(rating["ratingValue"]).replace(",", ".")
    except (TypeError, ValueError, OverflowError):
        return None


class HTMLMetadataMixin:
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
                return html.unescape(val.strip())
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
        img = schema.get("image") or schema.get("thumbnailUrl")
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
        if rating := json_ld_rating_value(schema):
            result["rating"] = rating

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

        if (duration := json_ld_duration_minutes(schema)) is not None:
            result["duration"] = duration

        return result
