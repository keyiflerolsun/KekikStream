# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.


"""HTML cards işlemleri."""

class HTMLCardsMixin:
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
