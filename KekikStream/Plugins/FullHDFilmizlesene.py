# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo
from parsel           import Selector
from Kekik.Sifreleme  import StringCodec
import json, re

class FullHDFilmizlesene(PluginBase):
    name        = "FullHDFilmizlesene"
    language    = "tr"
    main_url    = "https://www.fullhdfilmizlesene.tv"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Türkiye'nin ilk ve lider HD film izleme platformu, kaliteli ve sorunsuz hizmetiyle sinema keyfini zirveye taşır."

    main_page   = {
        f"{main_url}/en-cok-izlenen-hd-filmler/"            : "En Çok izlenen Filmler",
        f"{main_url}/filmizle/aile-filmleri-hdf-izle/"      : "Aile Filmleri",
        f"{main_url}/filmizle/aksiyon-filmleri-hdf-izle/"   : "Aksiyon Filmleri",
        f"{main_url}/filmizle/animasyon-filmleri-izle/"     : "Animasyon Filmleri",
        f"{main_url}/filmizle/belgesel-filmleri-izle/"      : "Belgeseller",
        f"{main_url}/filmizle/bilim-kurgu-filmleri-izle-2/" : "Bilim Kurgu Filmleri",
        f"{main_url}/filmizle/bluray-filmler-izle/"         : "Blu Ray Filmler",
        f"{main_url}/filmizle/cizgi-filmler-fhd-izle/"      : "Çizgi Filmler",
        f"{main_url}/filmizle/dram-filmleri-hd-izle/"       : "Dram Filmleri",
        f"{main_url}/filmizle/fantastik-filmler-hd-izle/"   : "Fantastik Filmler",
        f"{main_url}/filmizle/gerilim-filmleri-fhd-izle/"   : "Gerilim Filmleri",
        f"{main_url}/filmizle/gizem-filmleri-hd-izle/"      : "Gizem Filmleri",
        f"{main_url}/filmizle/hint-filmleri-fhd-izle/"      : "Hint Filmleri",
        f"{main_url}/filmizle/komedi-filmleri-fhd-izle/"    : "Komedi Filmleri",
        f"{main_url}/filmizle/korku-filmleri-izle-3/"       : "Korku Filmleri",
        f"{main_url}/filmizle/macera-filmleri-fhd-izle/"    : "Macera Filmleri",
        f"{main_url}/filmizle/muzikal-filmler-izle/"        : "Müzikal Filmler",
        f"{main_url}/filmizle/polisiye-filmleri-izle/"      : "Polisiye Filmleri",
        f"{main_url}/filmizle/psikolojik-filmler-izle/"     : "Psikolojik Filmler",
        f"{main_url}/filmizle/romantik-filmler-fhd-izle/"   : "Romantik Filmler",
        f"{main_url}/filmizle/savas-filmleri-fhd-izle/"     : "Savaş Filmleri",
        f"{main_url}/filmizle/suc-filmleri-izle/"           : "Suç Filmleri",
        f"{main_url}/filmizle/tarih-filmleri-fhd-izle/"     : "Tarih Filmleri",
        f"{main_url}/filmizle/western-filmler-hd-izle-3/"   : "Western Filmler",
        f"{main_url}/filmizle/yerli-filmler-hd-izle/"       : "Yerli Filmler"
    }

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

    async def load_links(self, url: str) -> list[dict]:
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

        response = []
        for link in link_list:
            link = f"https:{link}" if link.startswith("//") else link
            data = await self.extract(link)
            if data:
                response.append(data)

        return response