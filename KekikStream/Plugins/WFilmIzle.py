# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper

class WFilmIzle(PluginBase):
    name        = "WFilmIzle"
    language    = "tr"
    main_url    = "https://www.wfilmizle.bar"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Yerli ve yabancı film izle, Türkçe dublaj ve altyazı seçenekleriyle en yeni ve unutulmamış olan filmleri Full HD kalitesinde online izleyebilirsiniz."

    main_page   = {
        f"{main_url}/"                                    : "Son Eklenenler",
        f"{main_url}/filmizle/aile-filmleri-izle-hd/"     : "Aile",
        f"{main_url}/filmizle/aksiyon-filmleri-izle-hd/"  : "Aksiyon",
        f"{main_url}/filmizle/animasyon-filmleri-izle/"   : "Animasyon",
        f"{main_url}/filmizle/belgesel-filmleri-izle/"    : "Belgesel",
        f"{main_url}/filmizle/bilim-kurgu-filmleri-izle/" : "Bilim Kurgu",
        f"{main_url}/filmizle/draam-filmleri-izle/"       : "Dram",
        f"{main_url}/filmizle/fantaastik-filmler-izle/"   : "Fantastik",
        f"{main_url}/filmizle/gerilimm-filmleri-izle/"    : "Gerilim",
        f"{main_url}/filmizle/gizem-filmleri-izle/"       : "Gizem",
        f"{main_url}/filmizle/komedi-filmleri-izle-hd/"   : "Komedi",
        f"{main_url}/filmizle/korkuu-filmleri-izle/"      : "Korku",
        f"{main_url}/filmizle/macera-filmleri-izle-hd/"   : "Macera",
        f"{main_url}/filmizle/polisiye-filmleri-izle-hd/" : "Polisiye",
        f"{main_url}/filmizle/romantik-filmler-izle/"     : "Romantik",
        f"{main_url}/filmizle/savas-filmmleri-izle/"      : "Savaş",
        f"{main_url}/filmizle/sporr-filmleri-izle/"       : "Spor",
        f"{main_url}/filmizle/succ-filmleri-izle/"        : "Suç",
        f"{main_url}/filmizle/tarih-filmleri-izle-hd/"    : "Tarih",
        f"{main_url}/filmizle/vahsi-bati-filmleri-izle/"  : "Vahşi Batı",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}/page/{page}" if page > 1 else url)
        secici = HTMLHelper(istek.text)

        if category == "Son Eklenenler":
            container = secici.select_first("div.fix-film_item")
            elements  = container.select("div.movie-preview-content") if container else []
        else:
            elements = secici.select("div.movie-preview-content")

        results = []
        for veri in elements:
            title  = (veri.select_text("span.movie-title") or "").replace(" izle", "").strip()
            href   = veri.select_attr("a", "href")
            poster = veri.select_attr("img", "data-src")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movie-preview-content"):
            title  = (veri.select_text("span.movie-title") or "").replace(" izle", "").strip()
            href   = veri.select_attr("a", "href")
            poster = veri.select_attr("img", "data-src")

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        org_title = (secici.select_text("div.title h1") or "").replace(" izle", "").strip()
        alt_title = (secici.select_text("div.diger_adi h2") or "").strip()
        title     = f"{org_title} - {alt_title}" if alt_title else org_title

        poster      = secici.select_attr("div.poster img", "src")
        description = secici.select_text("div.excerpt")
        year        = secici.select_text("div.release a")
        tags        = secici.select_texts("div.categories a")
        rating      = ""
        for imdb_div in secici.select("div.imdb"):
            text = imdb_div.text(strip=True)
            if "IMDb Puanı:" in text:
                rating = text.replace("IMDb Puanı:", "").split("/")[0].strip()
                break
        actors      = secici.select_texts("div.actor a")

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            year        = year,
            actors      = actors,
            rating      = rating or None,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        import time
        cookie_val = str(int(time.time()) - 50)

        istek  = await self.httpx.get(url, cookies={"session_starttime": cookie_val})
        secici = HTMLHelper(istek.text)

        # data-wpfc-original-src (WP Fastest Cache) → src fallback
        iframe_src = ""
        for ifr in secici.select("iframe"):
            src = ifr.select_attr(None, "data-wpfc-original-src") or ifr.select_attr(None, "src") or ""
            if src and "youtube" not in src and "a-ads" not in src:
                iframe_src = src
                break

        iframe_src = self.fix_url(iframe_src)

        if not iframe_src:
            return []

        response = []
        data     = await self.extract(iframe_src, referer=f"{self.main_url}/")
        self.collect_results(response, data)

        return response
