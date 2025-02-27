# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import kekik_cache, PluginBase, MainPageResult, SearchResult, MovieInfo
from parsel           import Selector
from Kekik.Sifreleme  import StringCodec
import json, re

class FullHDFilmizlesene(PluginBase):
    name        = "FullHDFilmizlesene"
    language    = "tr"
    main_url    = "https://www.fullhdfilmizlesene.de"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Sinema zevkini evinize kadar getirdik. Türkiye'nin lider Film sitesinde, en yeni filmleri Full HD izleyin."

    main_page   = {
        f"{main_url}/en-cok-izlenen-filmler-izle-hd/"            : "En Çok izlenen Filmler",
        f"{main_url}/filmizle/imdb-puani-yuksek-filmler-izle-1/" : "IMDB Puanı Yüksek Filmler",
        f"{main_url}/filmizle/aile-filmleri-izle-2/"             : "Aile Filmleri",
        f"{main_url}/filmizle/aksiyon-filmler-izle-1/"           : "Aksiyon Filmleri",
        f"{main_url}/filmizle/animasyon-filmleri-izle-4/"        : "Animasyon Filmleri",
        f"{main_url}/filmizle/belgesel-filmleri-izle-2/"         : "Belgeseller",
        f"{main_url}/filmizle/bilim-kurgu-filmleri-izle-1/"      : "Bilim Kurgu Filmleri",
        f"{main_url}/filmizle/bluray-filmler-izle-1/"            : "Blu Ray Filmler",
        f"{main_url}/filmizle/cizgi-filmler-izle-1/"             : "Çizgi Filmler",
        f"{main_url}/filmizle/dram-filmleri-izle/"               : "Dram Filmleri",
        f"{main_url}/filmizle/fantastik-filmleri-izle-2/"        : "Fantastik Filmler",
        f"{main_url}/filmizle/gerilim-filmleri-izle-3/"          : "Gerilim Filmleri",
        f"{main_url}/filmizle/gizem-filmleri-izle/"              : "Gizem Filmleri",
        f"{main_url}/filmizle/hint-filmler-fh-hd-izle/"          : "Hint Filmleri",
        f"{main_url}/filmizle/komedi-filmleri-izle-2/"           : "Komedi Filmleri",
        f"{main_url}/filmizle/korku-filmleri-izle-2/"            : "Korku Filmleri",
        f"{main_url}/filmizle/macera-filmleri-izle-1/"           : "Macera Filmleri",
        f"{main_url}/filmizle/muzikal-filmleri-izle/"            : "Müzikal Filmler",
        f"{main_url}/filmizle/polisiye-filmleri-izle-1/"         : "Polisiye Filmleri",
        f"{main_url}/filmizle/psikolojik-filmleri-izle/"         : "Psikolojik Filmler",
        f"{main_url}/filmizle/romantik-filmler-izle-1/"          : "Romantik Filmler",
        f"{main_url}/filmizle/savas-filmleri-izle-2/"            : "Savaş Filmleri",
        f"{main_url}/filmizle/suc-filmleri-izle-3/"              : "Suç Filmleri",
        f"{main_url}/filmizle/tarih-filmleri-izle/"              : "Tarih Filmleri",
        f"{main_url}/filmizle/western-filmleri-izle/"            : "Western Filmler",
        f"{main_url}/filmizle/yerli-filmler-izle-3/"             : "Yerli Filmler",
    }

    @kekik_cache(ttl=60*60)
    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = self.cloudscraper.get(f"{url}{page}")
        secici = Selector(istek.text)

        return [
            MainPageResult(
                category = category,
                title    = veri.css("span.film-title::text").get(),
                url      = self.fix_url(veri.css("a::attr(href)").get()),
                poster   = self.fix_url(veri.css("img::attr(data-src)").get()),
            )
                for veri in secici.css("li.film")
        ]

    @kekik_cache(ttl=60*60)
    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/arama/{query}")
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

    @kekik_cache(ttl=60*60)
    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
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

    @kekik_cache(ttl=15*60)
    async def load_links(self, url: str) -> list[str]:
        istek  = await self.httpx.get(url)
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