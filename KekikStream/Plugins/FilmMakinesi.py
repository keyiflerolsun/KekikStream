# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, SearchResult, MovieInfo
from parsel           import Selector

class FilmMakinesi(PluginBase):
    name     = "FilmMakinesi"
    main_url = "https://filmmakinesi.de"

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.oturum.get(f"{self.main_url}/?s={query}")
        secici = Selector(istek.text)

        results = []
        for article in secici.css("section#film_posts article"):
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
        istek  = await self.oturum.get(url)
        secici = Selector(istek.text)

        title       = secici.css("h1.single_h1 a::text").get().strip()
        poster      = secici.css("[property='og:image']::attr(content)").get().strip()
        description = secici.css("section#film_single article p:last-of-type::text").get().strip()
        tags        = secici.css("dt:contains('Tür:') + dd a::text").get().strip()
        rating      = secici.css("dt:contains('IMDB Puanı:') + dd::text").get().strip()
        year        = secici.css("dt:contains('Yapım Yılı:') + dd a::text").get().strip()
        actors      = secici.css("dt:contains('Oyuncular:') + dd::text").get().strip()
        duration    = secici.css("dt:contains('Film Süresi:') + dd time::attr(datetime)").get().strip()

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
        istek  = await self.oturum.get(url)
        secici = Selector(istek.text)

        iframe_src = secici.css("div.player-div iframe::attr(src)").get() or secici.css("div.player-div iframe::attr(data-src)").get()
        return [self.fix_url(iframe_src)] if iframe_src else []