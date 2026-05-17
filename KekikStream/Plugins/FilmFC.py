# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper
import json

class FilmFC(PluginBase):
    name        = "FilmFC"
    language    = "tr"
    main_url    = "https://www.filmfc.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "FilmFC, en yeni erotik filmleri Full HD kalitesinde sunan bir platformdur."

    main_page   = {
        f"{main_url}"                                       : "En Yeniler",
        f"{main_url}/erotikfilmler/abd-erotik"              : "ABD",
        f"{main_url}/erotikfilmler/alman-erotik"            : "Alman",
        f"{main_url}/erotikfilmler/erotik-filmler"          : "Erotik Filmler",
        f"{main_url}/erotikfilmler/fransiz-erotik"          : "Fransız",
        f"{main_url}/erotikfilmler/hint-erotik"             : "Hint",
        f"{main_url}/erotikfilmler/ispanyol-erotik"         : "İspanyol",
        f"{main_url}/erotikfilmler/italyan-erotik"          : "İtalyan",
        f"{main_url}/erotikfilmler/japon-erotik"            : "Japon",
        f"{main_url}/erotikfilmler/konulu-erotik"           : "Konulu",
        f"{main_url}/erotikfilmler/kore-erotik"             : "Kore",
        f"{main_url}/erotikfilmler/lezbiyen-erotik"         : "Lezbiyen",
        f"{main_url}/erotikfilmler/olgun-erotik"            : "Olgun",
        f"{main_url}/erotikfilmler/rus-erotik"              : "Rus",
        f"{main_url}/erotikfilmler/turkce-altyazili-erotik" : "Türkçe Altyazılı",
        f"{main_url}/erotikfilmler/turkce-dublaj-erotik"    : "Türkçe Dublaj",
        f"{main_url}/erotikfilmler/yabanci-erotik"          : "Yabancı",
        f"{main_url}/erotikfilmler/yerli-filmler"           : "Yerli Filmler",
        f"{main_url}/erotikfilmler/yesilcam-erotik"         : "Yeşilçam",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        full_url = f"{url}/page/{page}/" if page > 1 else url
        istek    = await self.async_cf_get(full_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.frag-k"):
            title  = item.select_attr("a.baslik", "title") or item.select_text("a.baslik")
            href   = item.select_attr("a.baslik", "href")
            poster = item.select_attr("img", "src") or item.select_attr("img", "data-src")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title.strip().replace(" izle", ""),
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.async_cf_get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.frag-k"):
            title  = item.select_attr("a.baslik", "title") or item.select_text("a.baslik")
            href   = item.select_attr("a.baslik", "href")
            poster = item.select_attr("img", "src") or item.select_attr("img", "data-src")

            if title and href:
                results.append(SearchResult(
                    title  = title.strip().replace(" izle", ""),
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))
        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        # JSON-LD metadata
        json_ld = secici.regex_first(r'application/ld\+json">({.*?})</script>')
        title   = ""
        poster  = ""
        if json_ld:
            try:
                data   = json.loads(json_ld)
                title  = data.get("name", "").replace(" izle", "")
                poster = data.get("image")
            except Exception:
                pass

        if not title:
            title = secici.select_text("title") or ""
            title = title.split("|")[0].split("-")[0].replace(" izle", "").strip()

        description = secici.select_text("div.movie-description") or secici.select_text("div.icerik")
        rating      = secici.select_text("span.imdb-rating") or secici.select_text("div.puan b")
        year        = secici.regex_first(r"\((\d{4})\)", secici.select_text("title") or "")
        tags        = secici.select_texts("div.movie-genres a") or secici.select_texts("div.detay b")

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        response   = []
        tried_urls = set()

        # Span#plyg içindeki iframe'i önceliklendir
        for iframe in secici.select("span#plyg iframe"):
            src = iframe.attrs.get("src")
            if src:
                src_fixed = self.fix_url(src)
                if src_fixed not in tried_urls:
                    tried_urls.add(src_fixed)
                    data = await self.extract(src_fixed, referer=url)
                    self.collect_results(response, data)

        # Diğer iframeler
        if not response:
            for iframe in secici.select("iframe"):
                src = iframe.attrs.get("src")
                if not src or any(x in src for x in ["youtube", "google", "facebook", "twitter"]):
                    continue

                src_fixed = self.fix_url(src)
                if src_fixed not in tried_urls:
                    tried_urls.add(src_fixed)
                    data = await self.extract(src_fixed, referer=url)
                    self.collect_results(response, data)

        return response
