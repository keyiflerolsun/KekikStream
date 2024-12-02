# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from Kekik.cli        import konsol
from KekikStream.Core import PluginBase, SearchResult, SeriesInfo, Episode
from parsel           import Selector
from json             import loads

class Dizilla(PluginBase):
    name     = "Dizilla"
    main_url = "https://dizilla.club"

    async def search(self, query: str) -> list[SearchResult]:
        ilk_istek  = await self.oturum.get(self.main_url)
        ilk_secici = Selector(ilk_istek.text)
        cKey       = ilk_secici.css("input[name='cKey']::attr(value)").get()
        cValue     = ilk_secici.css("input[name='cValue']::attr(value)").get()

        self.oturum.headers.update({
            "Accept"           : "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With" : "XMLHttpRequest",
            "Referer"          : f"{self.main_url}/"
        })
        self.oturum.cookies.update({
            "showAllDaFull"   : "true",
            "PHPSESSID"       : ilk_istek.cookies.get("PHPSESSID"),
        })

        arama_istek = await self.oturum.post(
            url  = f"{self.main_url}/bg/searchcontent",
            data = {
                "cKey"       : cKey,
                "cValue"     : cValue,
                "searchterm" : query
            }
        )
        arama_veri = arama_istek.json().get("data", {}).get("result", [])

        return [
            SearchResult(
                title  = veri.get("object_name"),
                url    = self.fix_url(f"{self.main_url}/{veri.get('used_slug')}"),
                poster = self.fix_url(veri.get("object_poster_url")),
            )
                for veri in arama_veri
        ]

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.oturum.get(url)
        secici = Selector(istek.text)
        veri   = loads(secici.xpath("//script[@type='application/ld+json']/text()").getall()[-1])

        title       = veri.get("name")
        if alt_title := veri.get("alternateName"):
            title += f" - ({alt_title})"

        poster      = self.fix_url(veri.get("image"))
        description = veri.get("description")
        year        = veri.get("datePublished").split("-")[0]
        tags        = []
        rating      = veri.get("aggregateRating", {}).get("ratingValue")
        actors      = [actor.get("name") for actor in veri.get("actor", []) if actor.get("name")]

        episodes = []
        for sezon in veri.get("containsSeason"):
            for bolum in sezon.get("episode"):
                episodes.append(Episode(
                    season  = sezon.get("seasonNumber"),
                    episode = bolum.get("episodeNumber"),
                    title   = bolum.get("name"),
                    url     = bolum.get("url"),
                ))

        return SeriesInfo(
            url         = url,
            poster      = poster,
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            episodes    = episodes,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[str]:
        konsol.print(url)
        istek  = await self.oturum.get(url)
        secici = Selector(istek.text)

        iframes = []
        # TODO: iframeleri getir kanks

        return iframes