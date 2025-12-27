# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult
from selectolax.parser import HTMLParser
import re

class UgurFilm(PluginBase):
    name        = "UgurFilm"
    language    = "tr"
    main_url    = "https://ugurfilm3.xyz"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Uğur Film ile film izle! En yeni ve güncel filmleri, Türk yerli filmleri Full HD 1080p kalitede Türkçe Altyazılı olarak izle."

    main_page   = {
        f"{main_url}/turkce-altyazili-filmler/page/" : "Türkçe Altyazılı Filmler",
        f"{main_url}/yerli-filmler/page/"            : "Yerli Filmler",
        f"{main_url}/en-cok-izlenen-filmler/page/"   : "En Çok İzlenen Filmler",
        f"{main_url}/category/kisa-film/page/"       : "Kısa Film",
        f"{main_url}/category/aksiyon/page/"         : "Aksiyon",
        f"{main_url}/category/bilim-kurgu/page/"     : "Bilim Kurgu",
        f"{main_url}/category/belgesel/page/"        : "Belgesel",
        f"{main_url}/category/komedi/page/"          : "Komedi",
        f"{main_url}/category/kara-film/page/"       : "Kara Film",
        f"{main_url}/category/erotik/page/"          : "Erotik"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}{page}", follow_redirects=True)
        secici = HTMLParser(istek.text)

        results = []
        for veri in secici.css("div.icerik div"):
            # Title is in the second span (a.baslik > span), not the first span (class="sol" which is empty)
            title_el = veri.css_first("a.baslik span")
            title = title_el.text(strip=True) if title_el else None
            if not title:
                continue

            link_el = veri.css_first("a")
            img_el  = veri.css_first("img")

            href   = link_el.attrs.get("href") if link_el else None
            poster = img_el.attrs.get("src") if img_el else None

            results.append(MainPageResult(
                category = category,
                title    = title,
                url      = self.fix_url(href) if href else "",
                poster   = self.fix_url(poster) if poster else None,
            ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLParser(istek.text)

        results = []
        for film in secici.css("div.icerik div"):
            # Title is in a.baslik > span, not the first span
            title_el = film.css_first("a.baslik span")
            title = title_el.text(strip=True) if title_el else None

            link_el = film.css_first("a")
            img_el  = film.css_first("img")

            href   = link_el.attrs.get("href") if link_el else None
            poster = img_el.attrs.get("src") if img_el else None

            if title and href:
                results.append(SearchResult(
                    title  = title.strip(),
                    url    = self.fix_url(href.strip()),
                    poster = self.fix_url(poster.strip()) if poster else None,
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)

        title_el = secici.css_first("div.bilgi h2")
        title    = title_el.text(strip=True) if title_el else ""

        poster_el = secici.css_first("div.resim img")
        poster    = poster_el.attrs.get("src", "").strip() if poster_el else ""

        desc_el     = secici.css_first("div.slayt-aciklama")
        description = desc_el.text(strip=True) if desc_el else ""

        tags = [a.text(strip=True) for a in secici.css("p.tur a[href*='/category/']") if a.text(strip=True)]

        # re_first yerine re.search
        year_el   = secici.css_first("a[href*='/yil/']")
        year_text = year_el.text(strip=True) if year_el else ""
        year_match = re.search(r"\d+", year_text)
        year = year_match.group() if year_match else None

        actors = []
        for actor in secici.css("li.oyuncu-k"):
            span_el = actor.css_first("span")
            if span_el and span_el.text(strip=True):
                actors.append(span_el.text(strip=True))

        return MovieInfo(
            url         = self.fix_url(url),
            poster      = self.fix_url(poster) if poster else None,
            title       = title,
            description = description,
            tags        = tags,
            year        = year,
            actors      = actors,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek   = await self.httpx.get(url)
        secici  = HTMLParser(istek.text)
        results = []

        part_links = [a.attrs.get("href") for a in secici.css("li.parttab a") if a.attrs.get("href")]

        for part_link in part_links:
            sub_response = await self.httpx.get(part_link)
            sub_selector = HTMLParser(sub_response.text)

            iframe_el = sub_selector.css_first("div#vast iframe")
            iframe = iframe_el.attrs.get("src") if iframe_el else None

            if iframe and self.main_url in iframe:
                post_data = {
                    "vid"         : iframe.split("vid=")[-1],
                    "alternative" : "vidmoly",
                    "ord"         : "0",
                }
                player_response = await self.httpx.post(
                    url  = f"{self.main_url}/player/ajax_sources.php",
                    data = post_data
                )
                iframe = self.fix_url(player_response.json().get("iframe"))
                data = await self.extract(iframe)
                if data:
                    results.append(data)

        return results