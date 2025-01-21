# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, SearchResult, SeriesInfo, Episode
from parsel           import Selector
from json             import loads
from urllib.parse     import urlparse, urlunparse

class Dizilla(PluginBase):
    name     = "Dizilla"
    main_url = "https://dizilla11.com"

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

    async def url_base_degis(self, eski_url:str, yeni_base:str) -> str:
        parsed_url       = urlparse(eski_url)
        parsed_yeni_base = urlparse(yeni_base)
        yeni_url         = parsed_url._replace(
            scheme = parsed_yeni_base.scheme,
            netloc = parsed_yeni_base.netloc
        )

        return urlunparse(yeni_url)

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

        bolumler = []
        sezonlar = veri.get("containsSeason") if isinstance(veri.get("containsSeason"), list) else [veri.get("containsSeason")]
        for sezon in sezonlar:
            for bolum in sezon.get("episode"):
                bolumler.append(Episode(
                    season  = sezon.get("seasonNumber"),
                    episode = bolum.get("episodeNumber"),
                    title   = bolum.get("name"),
                    url     = await self.url_base_degis(bolum.get("url"), self.main_url),
                ))

        return SeriesInfo(
            url         = url,
            poster      = poster,
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            episodes    = bolumler,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[str]:
        istek  = await self.oturum.get(url)
        secici = Selector(istek.text)

        iframes = [self.fix_url(secici.css("div#playerLsDizilla iframe::attr(src)").get())]
        for alternatif in secici.css("a[href*='player']"):
            alt_istek  = await self.oturum.get(self.fix_url(alternatif.css("::attr(href)").get()))
            alt_secici = Selector(alt_istek.text)
            iframes.append(self.fix_url(alt_secici.css("div#playerLsDizilla iframe::attr(src)").get()))

        return iframes