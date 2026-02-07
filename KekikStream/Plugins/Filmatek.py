# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper
from urllib.parse     import unquote
from contextlib       import suppress

class Filmatek(PluginBase):
    name        = "Filmatek"
    language    = "tr"
    main_url    = "https://filmatek.net"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Sosyalizmin Sineması Veritabanı"

    main_page = {
        f"{main_url}/tur/aile/page"             : "Aile",
        f"{main_url}/tur/aksiyon/page"          : "Aksiyon",
        f"{main_url}/tur/animasyon/page"        : "Animasyon",
        f"{main_url}/tur/bilim-kurgu/page"      : "Bilim Kurgu",
        f"{main_url}/tur/komedi/page"           : "Komedi",
        f"{main_url}/tur/korku/page"            : "Korku",
        f"{main_url}/tur/macera/page"           : "Macera",
        f"{main_url}/tur/romantik/page"         : "Romantik",
        f"{main_url}/tur/suc/page"              : "Suç",
        f"{main_url}/tur/yerli-filmler/page"    : "Yerli Filmler",
        f"{main_url}/film-arsivi/page"          : "Tüm Filmler",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}/{page}/")
        secici = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.items article, #archive-content article"):
            title_el = secici.select_first("div.data h3 a, h3 a", item)
            if not title_el:
                continue

            title  = title_el.text(strip=True)
            href   = self.fix_url(title_el.attrs.get("href"))
            poster = self.fix_url(secici.select_poster("img", item))

            results.append(MainPageResult(
                category = category,
                title    = title,
                url      = href,
                poster   = poster
            ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.result-item"):
            title_el = secici.select_first("div.title a", item)
            if not title_el:
                continue

            title  = title_el.text(strip=True)
            href   = self.fix_url(title_el.attrs.get("href"))
            poster = self.fix_url(secici.select_poster("div.image img", item))

            results.append(SearchResult(
                title  = title,
                url    = href,
                poster = poster
            ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = self.clean_title(secici.select_text("div.data h1, h1"))
        poster      = secici.select_poster("div.poster img") or secici.select_attr("meta[property='og:image']", "content")
        description = secici.select_text("div.wp-content p") or secici.select_attr("meta[property='og:description']", "content")
        year        = secici.extract_year("span.date")
        rating      = secici.select_text("span.dt_rating_vgs") or secici.select_text("span.dt_rating_vmanual")
        duration    = secici.regex_first(r"(\d+)", secici.select_text("span.runtime"))
        tags        = secici.select_texts("div.sgeneros a")
        actors      = secici.select_texts("div.person div.name a")

        return MovieInfo(
            url         = url,
            title       = title,
            description = description,
            poster      = self.fix_url(poster),
            year        = year,
            rating      = rating,
            duration    = duration,
            tags        = tags,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        # Player seçeneklerini bul
        options = secici.select("div#playeroptions ul.ajax_mode li.dooplay_player_option")
        if not options:
            # Fallback: Body class'tan post_id
            body_class = secici.select_attr("body", "class") or ""
            if pid := secici.regex_first(r"postid-(\d+)", body_class):
                options = [{"data-post": pid, "data-nume": "1", "data-type": "movie", "title": "Varsayılan"}]
            else:
                 options = []

        results = []
        for opt in options:
            if isinstance(opt, dict):
                post_id = opt.get("data-post")
                nume    = opt.get("data-nume")
                type_   = opt.get("data-type")
                title   = opt.get("title")
            else:
                post_id = opt.attrs.get("data-post")
                nume    = opt.attrs.get("data-nume")
                type_   = opt.attrs.get("data-type")
                title   = secici.select_text("span.title", opt)

            if not post_id or not nume:
                continue

            try:
                # Need to use post with data
                player_resp = await self.httpx.post(
                    url     = f"{self.main_url}/wp-admin/admin-ajax.php",
                    headers = {
                        "X-Requested-With" : "XMLHttpRequest",
                        "Referer"          : url,
                        "Content-Type"     : "application/x-www-form-urlencoded"
                    },
                    data    = {
                        "action" : "doo_player_ajax",
                        "post"   : post_id,
                        "nume"   : nume,
                        "type"   : type_
                    }
                )

                content    = player_resp.text.replace(r"\/", "/")
                iframe_url = secici.regex_first(r'(?:src|url)["\']?\s*[:=]\s*["\']([^"\']+)["\']', content)

                if iframe_url:
                    if iframe_url.startswith("/"):
                        iframe_url = self.main_url + iframe_url

                    iframe_url = self.fix_url(iframe_url)

                    # Unwrap internal JWPlayer
                    if "jwplayer/?source=" in iframe_url:
                        with suppress(Exception):
                            raw_source = iframe_url.split("source=")[1].split("&")[0]
                            iframe_url = unquote(raw_source)

                    # Direct media files
                    if ".m3u8" in iframe_url or ".mp4" in iframe_url:
                        results.append(ExtractResult(
                            name    = f"{title} | Direct",
                            url     = iframe_url,
                            referer = url
                        ))
                    else:
                        extracted = await self.extract(iframe_url, prefix=title)
                        if extracted:
                            if isinstance(extracted, list):
                                results.extend(extracted)
                            else:
                                results.append(extracted)
                        else:
                            results.append(ExtractResult(
                                name    = f"{title} | External",
                                url     = iframe_url,
                                referer = url
                            ))
            except Exception as e:
                # print(f"Filmatek Error: {e}")
                pass

        return results
