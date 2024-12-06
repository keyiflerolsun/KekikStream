# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.CLI  import konsol
from KekikStream.Core import PluginBase, SearchResult, MovieInfo
from parsel           import Selector
from Kekik.Sifreleme  import StringCodec
import json, re

class FullHDFilmizlesene(PluginBase):
    name     = "FullHDFilmizlesene"
    main_url = "https://www.fullhdfilmizlesene.de"

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.oturum.get(f"{self.main_url}/arama/{query}")
        secici = Selector(istek.text)

        results = []
        for film in secici.css("li.film"):
            title  = film.css("span.film-title::text").get()
            href   = film.css("a::attr(href)").get()
            poster = film.css("img::attr(data-src)").get()

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

        title       = secici.xpath("normalize-space(//div[@class='izle-titles'])").get().strip()
        poster      = secici.css("div img::attr(data-src)").get().strip()
        description = secici.css("div.ozet-ic p::text").get().strip()
        tags        = secici.css("a[rel='category tag']::text").getall()
        rating      = secici.xpath("normalize-space(//div[@class='puanx-puan'])").get().split()[-1]
        year        = secici.css("div.dd a.category::text").get().strip().split()[0]
        actors      = secici.css("div.film-info ul li:nth-child(2) a > span::text").getall()
        duration    = secici.css("span.sure::text").get("0 Dakika").split()[0]

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors,
            duration    = duration
        )

    async def load_links(self, url: str) -> list[str]:
        istek  = await self.oturum.get(url)
        secici = Selector(istek.text)

        script   = secici.xpath("(//script)[1]").get()
        scx_data = json.loads(re.findall(r"scx = (.*?);", script)[0])
        scx_keys = list(scx_data.keys())

        link_list = []
        for key in scx_keys:
            t = scx_data[key]["sx"]["t"]
            if isinstance(t, list):
                link_list.extend(StringCodec.decode(elem) for elem in t)
            if isinstance(t, dict):
                link_list.extend(StringCodec.decode(v) for k, v in t.items())

        return [
            f"https:{link}" if link.startswith("//") else link
                for link in link_list
        ]