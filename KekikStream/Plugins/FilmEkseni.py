# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper

class FilmEkseni(PluginBase):
    name        = "FilmEkseni"
    language    = "tr"
    main_url    = "https://filmekseni.cc"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "FilmEkseni, en yeni filmleri Full HD kalitesinde, Türkçe dublaj ve altyazı seçenekleriyle sunan bir film platformudur."

    main_page   = {
        f"{main_url}/"                          : "Son Eklenenler",
        f"{main_url}/en-cok-izlenenler/"        : "En Çok İzlenenler",
        f"{main_url}/imdb-250/"                 : "IMDb 250",
        f"{main_url}/tur/aile-filmleri/"        : "Aile",
        f"{main_url}/tur/aksiyon-filmleri/"     : "Aksiyon",
        f"{main_url}/tur/animasyon-film-izle/"  : "Animasyon",
        f"{main_url}/tur/bilim-kurgu-filmleri/" : "Bilim Kurgu",
        f"{main_url}/tur/fantastik-filmler/"    : "Fantastik",
        f"{main_url}/tur/gerilim-filmleri/"     : "Gerilim",
        f"{main_url}/tur/komedi-filmleri/"      : "Komedi",
        f"{main_url}/tur/korku-filmleri/"       : "Korku",
        f"{main_url}/tur/macera-film-izle/"     : "Macera",
        f"{main_url}/tur/suc-filmleri/"         : "Suç",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        full_url = f"{url.rstrip('/')}/page/{page}/" if page > 1 else url
        istek    = await self.async_cf_get(full_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.poster"):
            title  = item.select_attr("img", "alt") or item.select_text("div.poster-title")
            href   = item.select_attr("a", "href")
            poster = item.select_attr("img", "data-src") or item.select_attr("img", "src")

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
        for item in secici.select("div.poster"):
            title  = item.select_attr("img", "alt") or item.select_text("div.poster-title")
            href   = item.select_attr("a", "href")
            poster = item.select_attr("img", "data-src") or item.select_attr("img", "src")

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

        title       = secici.select_text("h1")
        poster      = secici.select_attr("img.img-movie", "data-src") or secici.select_attr("img.img-movie", "src")
        description = secici.select_text("div.movie-text")
        rating      = secici.select_text("span.imdb-rating")
        year        = secici.regex_first(r"\((\d{4})\)", secici.select_text("h1") or "")
        tags        = secici.select_texts("div.movie-genres a")
        actors      = secici.select_texts("div.movie-actors a")
        duration    = secici.extract_duration("movie-info")

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors,
            duration    = duration,
            imdb_id     = secici.regex_first(r"imdb\.com/title/(tt\d+)", istek.text),
            tmdb_id     = secici.regex_first(r"tmdb\.org/movie/(\d+)", istek.text)
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        response = []
        # Tab iframelerini bul
        for iframe in secici.select("div.tab-pane iframe, div.card-video iframe"):
            src = iframe.attrs.get("data-src") or iframe.attrs.get("src")
            if not src or "youtube" in src or "fragman" in src.lower():
                continue

            data = await self.extract(self.fix_url(src), referer=url)
            self.collect_results(response, data)

        # Diğer iframeler
        if not response:
            for iframe in secici.select("iframe"):
                src = iframe.attrs.get("data-src") or iframe.attrs.get("src")
                if src and "youtube" not in src and "fragman" not in src.lower():
                    data = await self.extract(self.fix_url(src), referer=url)
                    self.collect_results(response, data)

        return response
