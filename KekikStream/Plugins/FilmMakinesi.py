# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, SearchResult, MovieInfo
from parsel           import Selector

class FilmMakinesi(PluginBase):
    name     = "FilmMakinesi"
    main_url = "https://filmmakinesi.de"

    async def search(self, query: str) -> list[SearchResult]:
        response = await self.oturum.get(f"{self.main_url}/?s={query}")
        selector = Selector(response.text)

        results = []
        for article in selector.css("section#film_posts article"):
            title  = article.css("h6 a::text").get()
            href   = article.css("h6 a::attr(href)").get()
            poster = article.css("img::attr(data-src)").get() or article.css("img::attr(src)").get()

            if title and href:
                results.append(
                    SearchResult(
                        title  = title.strip(),
                        url    = self.fix_url(href.strip()),
                        poster = self.fix_url(poster.strip()) if poster else None,
                    )
                )

        return results

    async def load_item(self, url: str) -> MovieInfo:
        response = await self.oturum.get(url)
        selector = Selector(response.text)

        title       = selector.css("h1.single_h1 a::text").get(default="").strip()
        poster      = selector.css("[property='og:image']::attr(content)").get(default="").strip()
        description = selector.css("section#film_single article p:last-of-type::text").get(default="").strip()
        tags        = selector.css("dt:contains('Tür:') + dd a::text").get(default="").strip()
        rating      = selector.css("dt:contains('IMDB Puanı:') + dd::text").get(default="").strip()
        year        = selector.css("dt:contains('Yapım Yılı:') + dd a::text").get(default="").strip()
        actors      = selector.css("dt:contains('Oyuncular:') + dd::text").get(default="").strip()
        duration    = selector.css("dt:contains('Film Süresi:') + dd time::attr(datetime)").get(default="").strip()

        duration_minutes = 0
        if duration and duration.startswith("PT") and duration.endswith("M"):
            duration_minutes = int(duration[2:-1])

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors,
            duration    = duration_minutes
        )

    async def load_links(self, url: str) -> list[str]:
        response = await self.oturum.get(url)
        selector = Selector(response.text)

        iframe_src = selector.css("div.player-div iframe::attr(src)").get() or selector.css("div.player-div iframe::attr(data-src)").get()
        return [self.fix_url(iframe_src)] if iframe_src else []