# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, SearchResult, MovieInfo
from parsel           import Selector

class UgurFilm(PluginBase):
    name     = "UgurFilm"
    main_url = "https://ugurfilm8.com"

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.oturum.get(f"{self.main_url}/?s={query}")
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

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.oturum.get(url)
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

    async def load_links(self, url: str) -> list[str]:
        istek   = await self.oturum.get(url)
        secici  = Selector(istek.text)
        results = []

        for part_link in secici.css("li.parttab a::attr(href)").getall():
            sub_response = await self.oturum.get(part_link)
            sub_selector = Selector(sub_response.text)

            iframe = sub_selector.css("div#vast iframe::attr(src)").get()
            if iframe and self.main_url in iframe:
                post_data = {
                    "vid"         : iframe.split("vid=")[-1],
                    "alternative" : "vidmoly",
                    "ord"         : "0",
                }
                player_response = await self.oturum.post(
                    url  = f"{self.main_url}/player/ajax_sources.php",
                    data = post_data
                )
                iframe = player_response.json().get("iframe")
                results.append(iframe)

        return results