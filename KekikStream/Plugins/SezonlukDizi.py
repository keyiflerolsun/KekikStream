# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import kekik_cache, PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode
from parsel           import Selector

class SezonlukDizi(PluginBase):
    name        = "SezonlukDizi"
    language    = "tr"
    main_url    = "https://sezonlukdizi6.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Güncel ve eski dizileri en iyi görüntü kalitesiyle bulabileceğiniz yabancı dizi izleme siteniz."

    main_page   = {
        f"{main_url}/diziler.asp?siralama_tipi=id&s="          : "Son Eklenenler",
        f"{main_url}/diziler.asp?siralama_tipi=id&tur=mini&s=" : "Mini Diziler",
        f"{main_url}/diziler.asp?siralama_tipi=id&kat=2&s="    : "Yerli Diziler",
        f"{main_url}/diziler.asp?siralama_tipi=id&kat=1&s="    : "Yabancı Diziler",
        f"{main_url}/diziler.asp?siralama_tipi=id&kat=3&s="    : "Asya Dizileri",
        f"{main_url}/diziler.asp?siralama_tipi=id&kat=4&s="    : "Animasyonlar",
        f"{main_url}/diziler.asp?siralama_tipi=id&kat=5&s="    : "Animeler",
        f"{main_url}/diziler.asp?siralama_tipi=id&kat=6&s="    : "Belgeseller",
    }

    @kekik_cache(ttl=60*60)
    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}{page}")
        secici = Selector(istek.text)

        return [
            MainPageResult(
                category = category,
                title    = veri.css("div.description::text").get(),
                url      = self.fix_url(veri.css("::attr(href)").get()),
                poster   = self.fix_url(veri.css("img::attr(data-src)").get()),
            )
                for veri in secici.css("div.afis a") if veri.css("div.description::text").get()
        ]

    @kekik_cache(ttl=60*60)
    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/diziler.asp?adi={query}")
        secici = Selector(istek.text)

        return [
            SearchResult(
                title  = afis.css("div.description::text").get().strip(),
                url    = self.fix_url(afis.attrib.get("href")),
                poster = self.fix_url(afis.css("img::attr(data-src)").get()),
            )
                for afis in secici.css("div.afis a.column")
        ]

    @kekik_cache(ttl=60*60)
    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        title       = secici.css("div.header::text").get().strip()
        poster      = self.fix_url(secici.css("div.image img::attr(data-src)").get().strip())
        year        = secici.css("div.extra span::text").re_first(r"(\d{4})")
        description = secici.xpath("normalize-space(//span[@id='tartismayorum-konu'])").get()
        tags        = secici.css("div.labels a[href*='tur']::text").getall()
        rating      = secici.css("div.dizipuani a div::text").re_first(r"[\d.,]+")
        actors      = []

        actors_istek  = await self.httpx.get(f"{self.main_url}/oyuncular/{url.split('/')[-1]}")
        actors_secici = Selector(actors_istek.text)
        actors = [
            actor.css("div.header::text").get().strip()
                for actor in actors_secici.css("div.doubling div.ui")
        ]

        episodes_istek  = await self.httpx.get(f"{self.main_url}/bolumler/{url.split('/')[-1]}")
        episodes_secici = Selector(episodes_istek.text)
        episodes        = []

        for sezon in episodes_secici.css("table.unstackable"):
            for bolum in sezon.css("tbody tr"):
                ep_name    = bolum.css("td:nth-of-type(4) a::text").get().strip()
                ep_href    = self.fix_url(bolum.css("td:nth-of-type(4) a::attr(href)").get())
                ep_episode = bolum.css("td:nth-of-type(3) a::text").re_first(r"(\d+)")
                ep_season  = bolum.css("td:nth-of-type(2)::text").re_first(r"(\d+)")

                if ep_name and ep_href:
                    episode = Episode(
                        season  = ep_season,
                        episode = ep_episode,
                        title   = ep_name,
                        url     = ep_href,
                    )
                    episodes.append(episode)

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

    @kekik_cache(ttl=15*60)
    async def load_links(self, url: str) -> list[str]:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        bid = secici.css("div#dilsec::attr(data-id)").get()
        if not bid:
            return []

        links = []
        for dil, label in [("1", "AltYazı"), ("0", "Dublaj")]:
            dil_istek = await self.httpx.post(
                url     = f"{self.main_url}/ajax/dataAlternatif22.asp",
                headers = {"X-Requested-With": "XMLHttpRequest"},
                data    = {"bid": bid, "dil": dil},
            )

            try:
                dil_json = dil_istek.json()
            except Exception:
                continue

            if dil_json.get("status") == "success":
                for veri in dil_json.get("data", []):
                    veri_response = await self.httpx.post(
                        url     = f"{self.main_url}/ajax/dataEmbed22.asp",
                        headers = {"X-Requested-With": "XMLHttpRequest"},
                        data    = {"id": veri.get("id")},
                    )
                    secici = Selector(veri_response.text)

                    if iframe := secici.css("iframe::attr(src)").get():
                        video_url = self.fix_url(iframe)
                        links.append(video_url)

        return links