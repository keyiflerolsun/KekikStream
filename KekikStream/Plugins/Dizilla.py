# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import kekik_cache, PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode
from parsel           import Selector
from json             import loads
from urllib.parse     import urlparse, urlunparse

class Dizilla(PluginBase):
    name        = "Dizilla"
    language    = "tr"
    main_url    = "https://dizilla.nl"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Dizilla tüm yabancı dizileri ücretsiz olarak Türkçe Dublaj ve altyazılı seçenekleri ile 1080P kalite izleyebileceğiniz yeni nesil yabancı dizi izleme siteniz."

    main_page   = {
        f"{main_url}/tum-bolumler"          : "Altyazılı Bölümler",
        f"{main_url}/dublaj-bolumler"       : "Dublaj Bölümler",
        f"{main_url}/dizi-turu/aile"        : "Aile",
        f"{main_url}/dizi-turu/aksiyon"     : "Aksiyon",
        f"{main_url}/dizi-turu/bilim-kurgu" : "Bilim Kurgu",
        f"{main_url}/dizi-turu/romantik"    : "Romantik",
        f"{main_url}/dizi-turu/komedi"      : "Komedi"
    }

    @kekik_cache(ttl=60*60)
    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        ana_sayfa = []

        if "dizi-turu" in url:
            ana_sayfa.extend([
                MainPageResult(
                    category = category,
                    title    = veri.css("h2::text").get(),
                    url      = self.fix_url(veri.css("::attr(href)").get()),
                    poster   = self.fix_url(veri.css("img::attr(src)").get() or veri.css("img::attr(data-src)").get())
                )
                    for veri in secici.css("div.grid-cols-3 a")
            ])
        else:
            for veri in secici.css("div.grid a"):
                name    = veri.css("h2::text").get()
                ep_name = veri.css("div.opacity-80::text").get()
                if not ep_name:
                    continue

                ep_name = ep_name.replace(". Sezon", "x").replace(". Bölüm", "").replace("x ", "x")
                title   = f"{name} - {ep_name}"

                ep_req    = await self.httpx.get(veri.css("::attr(href)").get())
                ep_secici = Selector(ep_req.text)
                href      = self.fix_url(ep_secici.css("a.relative::attr(href)").get())
                poster    = self.fix_url(ep_secici.css("img.imgt::attr(onerror)").get().split("= '")[-1].split("';")[0])

                ana_sayfa.append(
                    MainPageResult(
                        category = category,
                        title    = title,
                        url      = href,
                        poster   = poster
                    )
                )

        return ana_sayfa

    @kekik_cache(ttl=60*60)
    async def search(self, query: str) -> list[SearchResult]:
        ilk_istek  = await self.httpx.get(self.main_url)
        ilk_secici = Selector(ilk_istek.text)
        cKey       = ilk_secici.css("input[name='cKey']::attr(value)").get()
        cValue     = ilk_secici.css("input[name='cValue']::attr(value)").get()

        self.httpx.headers.update({
            "Accept"           : "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With" : "XMLHttpRequest",
            "Referer"          : f"{self.main_url}/"
        })
        self.httpx.cookies.update({
            "showAllDaFull"   : "true",
            "PHPSESSID"       : ilk_istek.cookies.get("PHPSESSID"),
        })

        arama_istek = await self.httpx.post(
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

    @kekik_cache(ttl=60*60)
    async def url_base_degis(self, eski_url:str, yeni_base:str) -> str:
        parsed_url       = urlparse(eski_url)
        parsed_yeni_base = urlparse(yeni_base)
        yeni_url         = parsed_url._replace(
            scheme = parsed_yeni_base.scheme,
            netloc = parsed_yeni_base.netloc
        )

        return urlunparse(yeni_url)

    @kekik_cache(ttl=60*60)
    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
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

    @kekik_cache(ttl=15*60)
    async def load_links(self, url: str) -> list[str]:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        iframes = [self.fix_url(secici.css("div#playerLsDizilla iframe::attr(src)").get())]
        for alternatif in secici.css("a[href*='player']"):
            alt_istek  = await self.httpx.get(self.fix_url(alternatif.css("::attr(href)").get()))
            alt_secici = Selector(alt_istek.text)
            iframes.append(self.fix_url(alt_secici.css("div#playerLsDizilla iframe::attr(src)").get()))

        return iframes