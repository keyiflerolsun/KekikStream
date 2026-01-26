# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper

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
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.icerik div"):
            # Title is in the second span (a.baslik > span), not the first span (class="sol" which is empty)
            title = secici.select_text("a.baslik span", veri)
            if not title:
                continue

            href = secici.select_attr("a", "href", veri)
            poster = secici.select_attr("img", "src", veri)

            results.append(MainPageResult(
                category = category,
                title    = title,
                url      = self.fix_url(href) if href else "",
                poster   = self.fix_url(poster) if poster else None,
            ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for film in secici.select("div.icerik div"):
            title = secici.select_text("a.baslik span", film)
            href = secici.select_attr("a", "href", film)
            poster = secici.select_attr("img", "src", film)

            if title and href:
                results.append(SearchResult(
                    title  = title.strip(),
                    url    = self.fix_url(href.strip()),
                    poster = self.fix_url(poster.strip()) if poster else None,
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("div.bilgi h2")
        poster      = secici.select_poster("div.resim img")
        description = secici.select_text("div.slayt-aciklama")
        tags        = secici.select_texts("p.tur a[href*='/category/']")
        year        = secici.extract_year("a[href*='/yil/']")
        actors      = secici.select_texts("li.oyuncu-k span")

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster) if poster else None,
            title       = title or "Bilinmiyor",
            description = description,
            tags        = tags,
            year        = str(year) if year else None,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek   = await self.httpx.get(url)
        secici  = HTMLHelper(istek.text)
        results = []

        part_links = secici.select_all_attr("li.parttab a", "href")

        for part_link in part_links:
            sub_response = await self.httpx.get(part_link)
            sub_selector = HTMLHelper(sub_response.text)

            iframe = sub_selector.select_attr("div#vast iframe", "src")

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