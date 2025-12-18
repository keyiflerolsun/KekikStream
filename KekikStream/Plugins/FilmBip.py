# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo
from parsel import Selector

class FilmBip(PluginBase):
    name        = "FilmBip"
    language    = "tr"
    main_url    = "https://filmbip.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "FilmBip adlı film sitemizde Full HD film izle. Yerli ve yabancı filmleri Türkçe dublaj veya altyazılı şekilde 1080p yüksek kalite film izle"

    main_page   = {
        f"{main_url}/filmler/SAYFA"                 : "Yeni Filmler",
        f"{main_url}/film/tur/aile/SAYFA"           : "Aile",
        f"{main_url}/film/tur/aksiyon/SAYFA"        : "Aksiyon",
        f"{main_url}/film/tur/belgesel/SAYFA"       : "Belgesel",
        f"{main_url}/film/tur/bilim-kurgu/SAYFA"    : "Bilim Kurgu",
        f"{main_url}/film/tur/dram/SAYFA"           : "Dram",
        f"{main_url}/film/tur/fantastik/SAYFA"      : "Fantastik",
        f"{main_url}/film/tur/gerilim/SAYFA"        : "Gerilim",
        f"{main_url}/film/tur/gizem/SAYFA"          : "Gizem",
        f"{main_url}/film/tur/komedi/SAYFA"         : "Komedi",
        f"{main_url}/film/tur/korku/SAYFA"          : "Korku",
        f"{main_url}/film/tur/macera/SAYFA"         : "Macera",
        f"{main_url}/film/tur/muzik/SAYFA"          : "Müzik",
        f"{main_url}/film/tur/romantik/SAYFA"       : "Romantik",
        f"{main_url}/film/tur/savas/SAYFA"          : "Savaş",
        f"{main_url}/film/tur/suc/SAYFA"            : "Suç",
        f"{main_url}/film/tur/tarih/SAYFA"          : "Tarih",
        f"{main_url}/film/tur/vahsi-bati/SAYFA"     : "Western",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        page_url = url.replace("SAYFA", "") if page == 1 else url.replace("SAYFA", str(page))
        page_url = page_url.rstrip("/")

        istek  = await self.httpx.get(page_url)
        secici = Selector(istek.text)

        results = []
        for veri in secici.css("div.poster-long"):
            img = veri.css("a.block img.lazy")
            title = img.css("::attr(alt)").get()
            href  = self.fix_url(veri.css("a.block::attr(href)").get())
            poster = self.fix_url(img.css("::attr(data-src)").get() or img.css("::attr(src)").get())

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = href,
                    poster   = poster,
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek = await self.httpx.post(
            url     = f"{self.main_url}/search",
            headers = {
                "Accept"           : "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With" : "XMLHttpRequest",
                "Content-Type"     : "application/x-www-form-urlencoded; charset=UTF-8",
                "Origin"           : self.main_url,
                "Referer"          : f"{self.main_url}/"
            },
            data    = {"query": query}
        )

        try:
            json_data = istek.json()
            if not json_data.get("success"):
                return []

            html_content = json_data.get("theme", "")
        except Exception:
            return []

        secici = Selector(text=html_content)

        results = []
        for veri in secici.css("li"):
            title  = veri.css("a.block.truncate::text").get()
            href   = self.fix_url(veri.css("a::attr(href)").get())
            poster = self.fix_url(veri.css("img.lazy::attr(data-src)").get())

            if title and href:
                results.append(SearchResult(
                    title  = title.strip(),
                    url    = href,
                    poster = poster,
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        title       = secici.css("div.page-title h1::text").get()
        poster      = self.fix_url(secici.css("meta[property='og:image']::attr(content)").get())
        trailer     = secici.css("div.series-profile-trailer::attr(data-yt)").get()
        description = secici.css("div.series-profile-infos-in.article p::text").get() or \
                      secici.css("div.series-profile-summary p::text").get()
        
        tags = secici.css("div.series-profile-type.tv-show-profile-type a::text").getall()

        # XPath ile yıl, süre ve puan
        year     = secici.xpath("//li[span[contains(text(), 'Yapım yılı')]]/p/text()").re_first(r"(\d{4})")
        duration = secici.xpath("//li[span[contains(text(), 'Süre')]]/p/text()").re_first(r"(\d+)")
        rating   = secici.xpath("//li[span[contains(text(), 'IMDB Puanı')]]/p/span/text()").get()

        actors = secici.css("div.series-profile-cast ul li a img::attr(alt)").getall()

        return MovieInfo(
            url         = url,
            poster      = poster,
            title       = self.clean_title(title) if title else "",
            description = description.strip() if description else None,
            tags        = tags,
            year        = year,
            rating      = rating,
            duration    = int(duration) if duration else None,
            actors      = actors,
        )

    async def load_links(self, url: str) -> list[dict]:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        results = []

        for player in secici.css("div#tv-spoox2"):
            iframe = self.fix_url(player.css("iframe::attr(src)").get())

            if iframe:
                extractor = self.ex_manager.find_extractor(iframe)
                results.append({
                    "name"    : extractor.name if extractor else "Player",
                    "url"     : iframe,
                    "referer" : f"{self.main_url}/"
                })

        return results
