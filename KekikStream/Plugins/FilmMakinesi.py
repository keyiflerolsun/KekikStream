# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult
from parsel           import Selector

class FilmMakinesi(PluginBase):
    name        = "FilmMakinesi"
    language    = "tr"
    main_url    = "https://filmmakinesi.to"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Film Makinesi ile en yeni ve güncel filmleri Full HD kalite farkı ile izleyebilirsiniz. Film izle denildiğinde akla gelen en kaliteli film sitesi."

    main_page   = {
        f"{main_url}/filmler-1/"                : "Son Filmler",
        f"{main_url}/tur/aksiyon-fm1/film/"     : "Aksiyon",
        f"{main_url}/tur/aile-fm1/film/"        : "Aile",
        f"{main_url}/tur/animasyon-fm2/film/"   : "Animasyon",
        f"{main_url}/tur/belgesel/film/"        : "Belgesel",
        f"{main_url}/tur/biyografi/film/"       : "Biyografi",
        f"{main_url}/tur/bilim-kurgu-fm3/film/" : "Bilim Kurgu",
        f"{main_url}/tur/dram-fm1/film/"        : "Dram",
        f"{main_url}/tur/fantastik-fm1/film/"   : "Fantastik",
        f"{main_url}/tur/gerilim-fm1/film/"     : "Gerilim",
        f"{main_url}/tur/gizem/film/"           : "Gizem",
        f"{main_url}/tur/komedi-fm1/film/"      : "Komedi",
        f"{main_url}/tur/korku-fm1/film/"       : "Korku",
        f"{main_url}/tur/macera-fm1/film/"      : "Macera",
        f"{main_url}/tur/muzik/film/"           : "Müzik",
        f"{main_url}/tur/polisiye/film/"        : "Polisiye",
        f"{main_url}/tur/romantik-fm1/film/"    : "Romantik",
        f"{main_url}/tur/savas-fm1/film/"       : "Savaş",
        f"{main_url}/tur/spor/film/"            : "Spor",
        f"{main_url}/tur/tarih/film/"           : "Tarih",
        f"{main_url}/tur/western-fm1/film/"     : "Western"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = self.cloudscraper.get(f"{url}{'' if page == 1 else f'page/{page}/'}")
        secici = Selector(istek.text)

        veriler = secici.css("div.item-relative")

        return [
            MainPageResult(
                category = category,
                title    = veri.css("div.title::text").get(),
                url      = self.fix_url(veri.css("a::attr(href)").get()),
                poster   = self.fix_url(veri.css("img::attr(data-src)").get() or veri.css("img::attr(src)").get()),
            )
                for veri in veriler
        ]

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/arama/?s={query}")
        secici = Selector(istek.text)

        results = []
        for article in secici.css("div.item-relative"):
            title  = article.css("div.title::text").get()
            href   = article.css("a::attr(href)").get()
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
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        title       = secici.css("h1.title::text").get()
        title       = title.strip() if title else ""
        poster      = secici.css("img.cover-img::attr(src)").get()
        poster      = poster.strip() if poster else ""
        description = secici.css("div.info-description p::text").get()
        description = description.strip() if description else ""
        rating      = secici.css("div.score::text").get()
        if rating:
            rating = rating.strip().split()[0]
        year        = secici.css("span.date a::text").get()
        year        = year.strip() if year else ""
        actors      = secici.css("div.cast-name::text").getall()
        tags        = secici.css("div.genre a::text").getall()
        duration    = secici.css("div.time::text").get()
        if duration:
            duration = duration.split()[1].strip() if len(duration.split()) > 1 else ""

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = self.clean_title(title),
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors,
            duration    = duration
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        response = []

        # Video parts linklerini ve etiketlerini al
        for link in secici.css("div.video-parts a[data-video_url]"):
            video_url = link.attrib.get("data-video_url")
            label     = link.css("::text").get() or ""
            label     = label.strip()

            data = await self.extract(video_url, prefix=label.split()[0] if label else None)
            if data:
                response.append(data)

        # Eğer video-parts yoksa iframe kullan
        if not response:
            iframe_src = secici.css("iframe::attr(data-src)").get()
            if iframe_src:
                data = await self.extract(iframe_src)
                if data:
                    response.append(data)

        return response
