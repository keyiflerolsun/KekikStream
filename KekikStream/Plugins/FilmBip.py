# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper

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
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.poster-long"):
            title = secici.select_attr("a.block img.lazy", "alt", veri)
            href = secici.select_attr("a.block", "href", veri)
            poster = secici.select_poster("a.block img.lazy", veri)

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster) if poster else None,
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

        secici = HTMLHelper(html_content)

        results = []
        for veri in secici.select("li"):
            title = secici.select_text("a.block.truncate", veri)
            href = secici.select_attr("a", "href", veri)
            poster = secici.select_attr("img.lazy", "data-src", veri)

            if title and href:
                results.append(SearchResult(
                    title  = title.strip(),
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster) if poster else None,
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = self.clean_title(secici.select_direct_text("div.page-title h1"))
        poster      = secici.select_poster("div.series-profile-image a img")
        description = secici.select_text("div.series-profile-infos-in.article p") or secici.select_text("div.series-profile-summary p")
        tags        = secici.select_texts("div.series-profile-type.tv-show-profile-type a")
        year        = secici.extract_year("div.series-profile-infos-in") or secici.regex_first(r"\((\d{4})\)", title)
        duration    = secici.regex_first(r"(\d+)", secici.meta_value("Süre", container_selector="div.series-profile-infos"))
        rating      = secici.meta_value("IMDB Puanı", container_selector="div.series-profile-infos")
        rating      = rating.split("(")[0] if rating else None
        actors      = secici.select_attrs("div.series-profile-cast ul li a img", "alt")

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster) if poster else None,
            title       = title or "",
            description = description,
            tags        = tags,
            year        = str(year) if year else None,
            rating      = rating,
            duration    = int(duration) if duration else None,
            actors      = actors,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        results = []

        for player in secici.select("div#tv-spoox2"):
            iframe    = secici.select_attr("iframe", "src", player)

            if iframe:
                iframe = self.fix_url(iframe)
                data = await self.extract(iframe)
                if data:
                    results.append(data)

        return results
