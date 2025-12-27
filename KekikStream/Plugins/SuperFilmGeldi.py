# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult
from selectolax.parser import HTMLParser
import re

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
        secici = HTMLParser(istek.text)

        results = []
        for veri in secici.css("div.movie-preview-content"):
            link_el = veri.css_first("span.movie-title a")
            if not link_el:
                continue

            title_text = link_el.text(strip=True)
            if not title_text:
                continue

            img_el = veri.css_first("img")
            href   = link_el.attrs.get("href")
            poster = img_el.attrs.get("src") if img_el else None

            results.append(MainPageResult(
                category = category,
                title    = self.clean_title(title_text.split(" izle")[0]),
                url      = self.fix_url(href) if href else "",
                poster   = self.fix_url(poster) if poster else None,
            ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}?s={query}")
        secici = HTMLParser(istek.text)

        results = []
        for veri in secici.css("div.movie-preview-content"):
            link_el = veri.css_first("span.movie-title a")
            if not link_el:
                continue

            title_text = link_el.text(strip=True)
            if not title_text:
                continue

            img_el = veri.css_first("img")
            href   = link_el.attrs.get("href")
            poster = img_el.attrs.get("src") if img_el else None

            results.append(SearchResult(
                title  = self.clean_title(title_text.split(" izle")[0]),
                url    = self.fix_url(href) if href else "",
                poster = self.fix_url(poster) if poster else None,
            ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)

        title_el = secici.css_first("div.title h1")
        title    = title_el.text(strip=True) if title_el else ""
        title    = self.clean_title(title.split(" izle")[0]) if title else ""

        poster_el = secici.css_first("div.poster img")
        poster    = poster_el.attrs.get("src") if poster_el else None

        # year: re_first kullanılamaz, re.search kullanıyoruz
        year_el   = secici.css_first("div.release a")
        year_text = year_el.text(strip=True) if year_el else ""
        year_match = re.search(r"(\d{4})", year_text)
        year = year_match.group(1) if year_match else None

        desc_el     = secici.css_first("div.excerpt p")
        description = desc_el.text(strip=True) if desc_el else None

        tags   = [a.text(strip=True) for a in secici.css("div.categories a") if a.text(strip=True)]
        actors = [a.text(strip=True) for a in secici.css("div.actor a") if a.text(strip=True)]

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster) if poster else None,
            title       = title,
            description = description,
            tags        = tags,
            year        = year,
            actors      = actors,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)

        iframe_el = secici.css_first("div#vast iframe")
        iframe    = iframe_el.attrs.get("src") if iframe_el else None
        iframe    = self.fix_url(iframe) if iframe else None

        if not iframe:
            return []

        results = []

        # Mix player özel işleme
        if "mix" in iframe and "index.php?data=" in iframe:
            iframe_istek = await self.httpx.get(iframe, headers={"Referer": f"{self.main_url}/"})
            mix_point    = re.search(r'videoUrl"\s*:\s*"(.*?)"\s*,\s*"videoServer', iframe_istek.text)

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
