# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import kekik_cache, PluginBase, MainPageResult, SearchResult, MovieInfo
from parsel           import Selector

class UgurFilm(PluginBase):
    name        = "UgurFilm"
    language    = "tr"
    main_url    = "https://ugurfilm8.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Yabancı film izle, Türkçe dublaj ve Türkçe altyazılı film seçenekleriyle 720p ve 1080p HD kalitesinde film izle - Uğur Film full hd film izle."

    main_page   = {
        f"{main_url}/turkce-altyazili-filmler/page/" : "Türkçe Altyazılı Filmler",
        f"{main_url}/yerli-filmler/page/"            : "Yerli Filmler",
        f"{main_url}/en-cok-izlenen-filmler/page/"   : "En Çok İzlenen Filmler",
        f"{main_url}/category/kisa-film/page/"       : "Kısa Film",
        f"{main_url}/category/aksiyon/page/"         : "Aksiyon",
        f"{main_url}/category/bilim-kurgu/page/"     : "Bilim Kurgu",
        f"{main_url}/category/belgesel/page/"        : "Belgesel",
        f"{main_url}/category/komedi/page/"          : "Komedi",
        f"{main_url}/category/kara-film/page/"       : "Kara Film",
        f"{main_url}/category/erotik/page/"          : "Erotik"
    }

    @kekik_cache(ttl=60*60)
    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}{page}", follow_redirects=True)
        secici = Selector(istek.text)

        return [
            MainPageResult(
                category = category,
                title    = veri.css("span:nth-child(1)::text").get(),
                url      = self.fix_url(veri.css("a::attr(href)").get()),
                poster   = self.fix_url(veri.css("img::attr(src)").get()),
            )
                for veri in secici.css("div.icerik div") if veri.css("span:nth-child(1)::text").get()
        ]

    @kekik_cache(ttl=60*60)
    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = Selector(istek.text)

        results = []
        for film in secici.css("div.icerik div"):
            title  = film.css("span:nth-child(1)::text").get()
            href   = film.css("a::attr(href)").get()
            poster = film.css("img::attr(src)").get()

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

        title       = secici.css("div.bilgi h2::text").get().strip()
        poster      = secici.css("div.resim img::attr(src)").get().strip()
        description = secici.css("div.slayt-aciklama::text").get().strip()
        tags        = secici.css("p.tur a[href*='/category/']::text").getall()
        year        = secici.css("a[href*='/yil/']::text").re_first(r"\d+")
        actors      = [actor.css("span::text").get() for actor in secici.css("li.oyuncu-k")]

        return MovieInfo(
            url         = self.fix_url(url),
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            year        = year,
            actors      = actors,
        )

    @kekik_cache(ttl=15*60)
    async def load_links(self, url: str) -> list[str]:
        istek   = await self.httpx.get(url)
        secici  = Selector(istek.text)
        results = []

        for part_link in secici.css("li.parttab a::attr(href)").getall():
            sub_response = await self.httpx.get(part_link)
            sub_selector = Selector(sub_response.text)

            iframe = sub_selector.css("div#vast iframe::attr(src)").get()
            if iframe and self.main_url in iframe:
                post_data = {
                    "vid"         : iframe.split("vid=")[-1],
                    "alternative" : "vidmoly",
                    "ord"         : "0",
                }
                player_response = await self.httpx.post(
                    url  = f"{self.main_url}/player/ajax_sources.php",
                    data = post_data
                )
                iframe = player_response.json().get("iframe")
                results.append(iframe)

        return results