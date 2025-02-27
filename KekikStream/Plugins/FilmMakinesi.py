# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import kekik_cache, PluginBase, MainPageResult, SearchResult, MovieInfo
from parsel           import Selector

class FilmMakinesi(PluginBase):
    name        = "FilmMakinesi"
    language    = "tr"
    main_url    = "https://filmmakinesi.de"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Film Makinesi, en yeni ve en güncel filmleri sitemizde full HD kalite farkı ile izleyebilirsiniz. HD film izle denildiğinde akla gelen en kaliteli film izleme sitesi."

    main_page   = {
        f"{main_url}/page/"                                        : "Son Filmler",
        f"{main_url}/film-izle/olmeden-izlenmesi-gerekenler/page/" : "Ölmeden İzle",
        f"{main_url}/film-izle/aksiyon-filmleri-izle/page/"        : "Aksiyon",
        f"{main_url}/film-izle/bilim-kurgu-filmi-izle/page/"       : "Bilim Kurgu",
        f"{main_url}/film-izle/macera-filmleri/page/"              : "Macera",
        f"{main_url}/film-izle/komedi-filmi-izle/page/"            : "Komedi",
        f"{main_url}/film-izle/romantik-filmler-izle/page/"        : "Romantik",
        f"{main_url}/film-izle/belgesel/page/"                     : "Belgesel",
        f"{main_url}/film-izle/fantastik-filmler-izle/page/"       : "Fantastik",
        f"{main_url}/film-izle/polisiye-filmleri-izle/page/"       : "Polisiye Suç",
        f"{main_url}/film-izle/korku-filmleri-izle-hd/page/"       : "Korku",
        f"{main_url}/film-izle/savas/page/"                        : "Tarihi ve Savaş",
        f"{main_url}/film-izle/gerilim-filmleri-izle/page/"        : "Gerilim Heyecan",
        f"{main_url}/film-izle/gizemli/page/"                      : "Gizem",
        f"{main_url}/film-izle/aile-filmleri/page/"                : "Aile",
        f"{main_url}/film-izle/animasyon-filmler/page/"            : "Animasyon",
        f"{main_url}/film-izle/western/page/"                      : "Western",
        f"{main_url}/film-izle/biyografi/page/"                    : "Biyografik",
        f"{main_url}/film-izle/dram/page/"                         : "Dram",
        f"{main_url}/film-izle/muzik/page/"                        : "Müzik",
        f"{main_url}/film-izle/spor/page/"                         : "Spor"
    }

    @kekik_cache(ttl=60*60)
    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = self.cloudscraper.get(f"{url}{page}")
        secici = Selector(istek.text)

        veriler = secici.css("section#film_posts article") if "/film-izle/" in url else secici.css("section#film_posts div.tooltip")

        return [
            MainPageResult(
                category = category,
                title    = veri.css("h6 a::text").get(),
                url      = self.fix_url(veri.css("h6 a::attr(href)").get()),
                poster   = self.fix_url(veri.css("img::attr(data-src)").get() or veri.css("img::attr(src)").get()),
            )
                for veri in veriler
        ]

    @kekik_cache(ttl=60*60)
    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
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

    @kekik_cache(ttl=60*60)
    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
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

    @kekik_cache(ttl=15*60)
    async def load_links(self, url: str) -> list[str]:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        iframe_src = secici.css("div.player-div iframe::attr(src)").get() or secici.css("div.player-div iframe::attr(data-src)").get()
        return [self.fix_url(iframe_src)] if iframe_src else []