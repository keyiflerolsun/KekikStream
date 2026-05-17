# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper

class DiziGom(PluginBase):
    name        = "DiziGom"
    language    = "tr"
    main_url    = "https://www.dizigom.love"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Türkçe altyazılı yabancı dizi izle, Tüm yabancı, kore, netflix dizilerin yeni ve eski sezonlarını orijinal dilinde dizigom1 alt yazılı film izleyebilir, sadece türkçe altyazılı en iyi yabancı diziler ve filmler hakkında yorum yapabilirsiniz."

    main_page   = {
        f"{main_url}/dizi-arsivi/?tur=Aile"        : "Aile",
        f"{main_url}/dizi-arsivi/?tur=Aksiyon"     : "Aksiyon",
        f"{main_url}/dizi-arsivi/?tur=Animasyon"   : "Animasyon",
        f"{main_url}/dizi-arsivi/?tur=Belgesel"    : "Belgesel",
        f"{main_url}/dizi-arsivi/?tur=Bilim Kurgu" : "Bilim Kurgu",
        f"{main_url}/dizi-arsivi/?tur=Dram"        : "Dram",
        f"{main_url}/dizi-arsivi/?tur=Fantazi"     : "Fantastik",
        f"{main_url}/dizi-arsivi/?tur=Gerilim"     : "Gerilim",
        f"{main_url}/dizi-arsivi/?tur=Komedi"      : "Komedi",
        f"{main_url}/dizi-arsivi/?tur=Korku"       : "Korku",
        f"{main_url}/dizi-arsivi/?tur=Macera"      : "Macera",
        f"{main_url}/dizi-arsivi/?tur=Romantik"    : "Romantik",
        f"{main_url}/dizi-arsivi/?tur=Savaş"       : "Savaş",
        f"{main_url}/dizi-arsivi/?tur=Suç"         : "Suç",
        f"{main_url}/dizi-arsivi/?tur=Tarih"       : "Tarih",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        if page > 1:
            parts = url.split("/?tur=")
            if len(parts) == 2:
                req_url = f"{parts[0]}/page/{page}/?tur={parts[1]}"
            else:
                req_url = f"{url}&page={page}"
        else:
            req_url = url

        istek  = await self.httpx.get(req_url)
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.single-item"):
            title  = veri.select_text("div.categorytitle a")
            href   = veri.select_attr("div.categorytitle a", "href")
            poster = veri.select_attr("div.cat-img img", "src") or veri.select_attr("img", "src")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title.strip(),
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.single-item"):
            title  = veri.select_text("div.categorytitle a")
            href   = veri.select_attr("div.categorytitle a", "href")
            poster = veri.select_attr("div.cat-img img", "src") or veri.select_attr("img", "src")

            if title and href:
                results.append(SearchResult(
                    title  = title.strip(),
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        # Dizi sayfası kontrolü
        title_border = secici.select_text("h1.title-border")
        if title_border:
            title = title_border.split(" izle")[0].split(" - Dizigom")[0].strip()

            poster      = secici.select_attr("div.category_image img", "src")
            description = secici.select_text("div.category_desc")

            # Metadata alanları
            year   = None
            actors = None
            rating = None

            for div in secici.select("div#icerikcat2 div"):
                text = div.text()
                if "Yapım Yılı" in text:
                    year = text.split("Yapım Yılı :")[-1].strip()
                elif "Oyuncular" in text:
                    actors = text.split("Oyuncular :")[-1].strip()
                elif "IMDB" in text:
                    rating = text.split("IMDB :")[-1].strip()

            tags = secici.select_texts("div.genres a")

            episodes = []
            for veri in secici.select("div.bolumust"):
                ep_href  = veri.select_attr("a", "href")
                ep_name  = veri.select_text("div.bolum-ismi")
                ep_title = veri.select_text("div.baslik") or ""

                parts   = ep_title.split()
                try:
                    season  = int(parts[0].replace(".", "")) if parts else 1
                except Exception:
                    season  = 1

                try:
                    episode = int(parts[2].replace(".", "")) if len(parts) > 2 else 1
                except Exception:
                    episode = 1

                if ep_href:
                    episodes.append(Episode(
                        season  = season,
                        episode = episode,
                        title   = ep_name or f"{season}. Sezon {episode}. Bölüm",
                        url     = self.fix_url(ep_href),
                    ))

            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = title,
                description = description,
                tags        = tags,
                year        = year,
                rating      = rating,
                actors      = actors,
                episodes    = episodes,
            )

        # Film sayfası — OG meta + JSON-LD (Fallback)
        og_title    = secici.select_attr("meta[property=\"og:title\"]", "content") or ""
        title       = og_title.split(" türkçe")[0].split(" izle")[0].strip() if og_title else ""
        poster      = secici.select_attr("meta[property=\"og:image\"]", "content") or ""
        og_desc     = secici.select_attr("meta[property=\"og:description\"]", "content") or ""
        description = og_desc.split(" türkçe")[0].split(" izle -")[0].strip() if og_desc else ""

        rating = secici.select_text("div.score") or secici.regex_first(r'"ratingValue"\s*:\s*"([^"]+)"')
        year   = secici.regex_first(r'"dateCreated"\s*:\s*"(\d{4})')

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            year        = year,
            rating      = rating,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url, headers={"Referer": f"{self.main_url}/"})
        secici = HTMLHelper(istek.text)

        # Video iframe bul
        iframe_src = secici.select_attr("div.video-container iframe", "src") or secici.select_attr("div.video iframe", "src")
        if not iframe_src:
            iframe_src = secici.select_attr("iframe", "src")

        if not iframe_src:
            return []

        return [await self.extract(self.fix_url(iframe_src))]
