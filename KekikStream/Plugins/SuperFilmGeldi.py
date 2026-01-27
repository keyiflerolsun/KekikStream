# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper

class SuperFilmGeldi(PluginBase):
    name        = "SuperFilmGeldi"
    language    = "tr"
    main_url    = "https://www.superfilmgeldi13.art"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Hd film izliyerek arkadaşlarınızla ve sevdiklerinizle iyi bir vakit geçirmek istiyorsanız açın bir film eğlenmeye bakın. Bilim kurgu filmleri, aşk drama vahşet aşk romantik sıradışı korku filmlerini izle."

    main_page   = {
        f"{main_url}/page/SAYFA"                                 : "Son Eklenenler",
        f"{main_url}/hdizle/category/aksiyon/page/SAYFA"         : "Aksiyon",
        f"{main_url}/hdizle/category/animasyon/page/SAYFA"       : "Animasyon",
        f"{main_url}/hdizle/category/belgesel/page/SAYFA"        : "Belgesel",
        f"{main_url}/hdizle/category/biyografi/page/SAYFA"       : "Biyografi",
        f"{main_url}/hdizle/category/bilim-kurgu/page/SAYFA"     : "Bilim Kurgu",
        f"{main_url}/hdizle/category/fantastik/page/SAYFA"       : "Fantastik",
        f"{main_url}/hdizle/category/dram/page/SAYFA"            : "Dram",
        f"{main_url}/hdizle/category/gerilim/page/SAYFA"         : "Gerilim",
        f"{main_url}/hdizle/category/gizem/page/SAYFA"           : "Gizem",
        f"{main_url}/hdizle/category/komedi-filmleri/page/SAYFA" : "Komedi Filmleri",
        f"{main_url}/hdizle/category/karete-filmleri/page/SAYFA" : "Karate Filmleri",
        f"{main_url}/hdizle/category/korku/page/SAYFA"           : "Korku",
        f"{main_url}/hdizle/category/muzik/page/SAYFA"           : "Müzik",
        f"{main_url}/hdizle/category/macera/page/SAYFA"          : "Macera",
        f"{main_url}/hdizle/category/romantik/page/SAYFA"        : "Romantik",
        f"{main_url}/hdizle/category/spor/page/SAYFA"            : "Spor",
        f"{main_url}/hdizle/category/savas/page/SAYFA"           : "Savaş",
        f"{main_url}/hdizle/category/suc/page/SAYFA"             : "Suç",
        f"{main_url}/hdizle/category/western/page/SAYFA"         : "Western",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(url.replace("SAYFA", str(page)))
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movie-preview-content"):
            title_text = secici.select_text("span.movie-title a", veri)
            if not title_text:
                continue

            href = secici.select_attr("span.movie-title a", "href", veri)
            poster = secici.select_attr("img", "src", veri)

            results.append(MainPageResult(
                category = category,
                title    = self.clean_title(title_text.split(" izle")[0]),
                url      = self.fix_url(href) if href else "",
                poster   = self.fix_url(poster),
            ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movie-preview-content"):
            title_text = secici.select_text("span.movie-title a", veri)
            if not title_text:
                continue

            href = secici.select_attr("span.movie-title a", "href", veri)
            poster = secici.select_attr("img", "src", veri)

            results.append(SearchResult(
                title  = self.clean_title(title_text.split(" izle")[0]),
                url    = self.fix_url(href) if href else "",
                poster = self.fix_url(poster),
            ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = self.clean_title(secici.select_text("div.title h1").split(" izle")[0]) if secici.select_text("div.title h1") else ""
        poster      = secici.select_poster("div.poster img")
        year        = secici.extract_year("div.release a")
        description = secici.select_text("div.excerpt p")
        tags        = secici.select_texts("div.categories a")
        actors      = secici.select_texts("div.actor a")

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            year        = year,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        iframe = secici.select_attr("div#vast iframe", "src")
        iframe = self.fix_url(iframe) if iframe else None

        if not iframe:
            return []

        results = []

        # Mix player özel işleme
        if "mix" in iframe and "index.php?data=" in iframe:
            iframe_istek = await self.httpx.get(iframe, headers={"Referer": f"{self.main_url}/"})
            iframe_sec = HTMLHelper(iframe_istek.text)
            mix_point    = iframe_sec.regex_first(r'videoUrl"\s*:\s*"(.*?)"\s*,\s*"videoServer')

            if mix_point:
                mix_point = mix_point.replace("\\", "")

                # Endpoint belirleme
                if "mixlion" in iframe:
                    end_point = "?s=3&d="
                elif "mixeagle" in iframe:
                    end_point = "?s=1&d="
                else:
                    end_point = "?s=0&d="

                m3u_link = iframe.split("/player")[0] + mix_point + end_point

                results.append(ExtractResult(
                    name      = f"{self.name} | Mix Player",
                    url       = m3u_link,
                    referer   = iframe,
                    subtitles = []
                ))
        else:
            # Extractor'a yönlendir
            data = await self.extract(iframe)
            if data:
                results.append(data)

        return results
