# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, SearchResult, MovieInfo
from parsel           import Selector

class UgurFilm(PluginBase):
    name     = "UgurFilm"
    main_url = "https://ugurfilm8.com"

    async def search(self, query: str) -> list[SearchResult]:
        response = await self.oturum.get(f"{self.main_url}/?s={query}")
        selector = Selector(response.text)

        results = []
        for article in selector.css("div.icerik div"):
            title  = article.css("span:nth-child(1)::text").get()
            href   = article.css("a::attr(href)").get()
            poster = article.css("img::attr(src)").get()

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

        title       = selector.css("div.bilgi h2::text").get(default="").strip()
        poster      = selector.css("div.resim img::attr(src)").get(default="").strip()
        description = selector.css("div.slayt-aciklama::text").get(default="").strip()
        tags        = selector.css("p.tur a[href*='/category/']::text").getall()
        year        = selector.css("a[href*='/yil/']::text").re_first(r"\d+")
        actors      = [actor.css("span::text").get() for actor in selector.css("li.oyuncu-k")]

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
        response = await self.oturum.get(url)
        selector = Selector(response.text)
        results  = []

        for part_link in selector.css("li.parttab a::attr(href)").getall():
            sub_response = await self.oturum.get(part_link)
            sub_selector = Selector(sub_response.text)

            iframe = sub_selector.css("div#vast iframe::attr(src)").get()
            if iframe and self.main_url in iframe:
                post_data = {
                    "vid"         : iframe.split("vid=")[-1],
                    "alternative" : "default",
                    "ord"         : "1",
                }
                player_response = await self.oturum.post(
                    url  = f"{self.main_url}/player/ajax_sources.php",
                    data = post_data
                )
                iframe = player_response.json().get("iframe")
                results.append(iframe)

        return results