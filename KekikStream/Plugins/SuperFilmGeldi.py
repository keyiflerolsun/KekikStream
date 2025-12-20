# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, Subtitle
from parsel import Selector
import re

class SuperFilmGeldi(PluginBase):
    name        = "SuperFilmGeldi"
    language    = "tr"
    main_url    = "https://www.superfilmgeldi13.art"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Hd film izliyerek arkadaşlarınızla ve sevdiklerinizle iyi bir vakit geçirmek istiyorsanız açın bir film eğlenmeye bakın. Bilim kurgu filmleri, aşk drama vahşet aşk romantik sıradışı korku filmlerini izle."

    main_page   = {
        f"{main_url}/page/SAYFA"                                        : "Son Eklenenler",
        f"{main_url}/hdizle/category/aksiyon/page/SAYFA"                : "Aksiyon",
        f"{main_url}/hdizle/category/animasyon/page/SAYFA"              : "Animasyon",
        f"{main_url}/hdizle/category/belgesel/page/SAYFA"               : "Belgesel",
        f"{main_url}/hdizle/category/bilim-kurgu/page/SAYFA"            : "Bilim Kurgu",
        f"{main_url}/hdizle/category/fantastik/page/SAYFA"              : "Fantastik",
        f"{main_url}/hdizle/category/komedi-filmleri/page/SAYFA"        : "Komedi Filmleri",
        f"{main_url}/hdizle/category/macera/page/SAYFA"                 : "Macera",
        f"{main_url}/hdizle/category/gerilim/page/SAYFA"                : "Gerilim",
        f"{main_url}/hdizle/category/suc/page/SAYFA"                    : "Suç",
        f"{main_url}/hdizle/category/karete-filmleri/page/SAYFA"        : "Karate Filmleri",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(url.replace("SAYFA", str(page)))
        secici = Selector(istek.text)

        return [
            MainPageResult(
                category = category,
                title    = self.clean_title(veri.css("span.movie-title a::text").get().split(" izle")[0]),
                url      = self.fix_url(veri.css("span.movie-title a::attr(href)").get()),
                poster   = self.fix_url(veri.css("img::attr(src)").get()),
            )
                for veri in secici.css("div.movie-preview-content")
                    if veri.css("span.movie-title a::text").get()
        ]

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}?s={query}")
        secici = Selector(istek.text)

        return [
            SearchResult(
                title  = self.clean_title(veri.css("span.movie-title a::text").get().split(" izle")[0]),
                url    = self.fix_url(veri.css("span.movie-title a::attr(href)").get()),
                poster = self.fix_url(veri.css("img::attr(src)").get()),
            )
                for veri in secici.css("div.movie-preview-content")
                    if veri.css("span.movie-title a::text").get()
        ]

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        title       = secici.css("div.title h1::text").get()
        title       = self.clean_title(title.split(" izle")[0]) if title else ""
        poster      = self.fix_url(secici.css("div.poster img::attr(src)").get())
        year        = secici.css("div.release a::text").re_first(r"(\d{4})")
        description = secici.css("div.excerpt p::text").get()
        tags        = secici.css("div.categories a::text").getall()
        actors      = secici.css("div.actor a::text").getall()

        return MovieInfo(
            url         = url,
            poster      = poster,
            title       = title,
            description = description,
            tags        = tags,
            year        = year,
            actors      = actors,
        )

    async def load_links(self, url: str) -> list[dict]:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        iframe = self.fix_url(secici.css("div#vast iframe::attr(src)").get())
        if not iframe:
            return []

        results = []

        # Mix player özel işleme
        if "mix" in iframe and "index.php?data=" in iframe:
            iframe_istek = await self.httpx.get(iframe, headers={"Referer": f"{self.main_url}/"})
            mix_point    = re.search(r'videoUrl":"(.*)","videoServer', iframe_istek.text)

            if mix_point:
                mix_point = mix_point[1].replace("\\", "")

                # Endpoint belirleme
                if "mixlion" in iframe:
                    end_point = "?s=3&d="
                elif "mixeagle" in iframe:
                    end_point = "?s=1&d="
                else:
                    end_point = "?s=0&d="

                m3u_link = iframe.split("/player")[0] + mix_point + end_point

                results.append({
                    "name"      : f"{self.name} | Mix Player",
                    "url"       : m3u_link,
                    "referer"   : iframe,
                    "subtitles" : []
                })
        else:
            extractor = self.ex_manager.find_extractor(iframe)
            results.append({
                "name"    : extractor.name if extractor else "Player",
                "url"     : iframe,
                "referer" : f"{self.main_url}/"
            })

        return results
