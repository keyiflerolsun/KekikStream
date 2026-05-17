# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper

class WFilmIzle(PluginBase):
    name        = "WFilmIzle"
    language    = "tr"
    main_url    = "https://www.wfilmizle.bar"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Wfilmizle, Full HD kalitesinde en yeni ve en güncel filmleri Türkçe dublaj ve altyazı seçenekleriyle sunan film izleme platformudur."

    main_page   = {
        f"{main_url}/"                                    : "En Yeniler",
        f"{main_url}/filmizle/aksiyon-filmleri-izle-hd/"  : "Aksiyon",
        f"{main_url}/filmizle/animasyon-filmleri-izle/"   : "Animasyon",
        f"{main_url}/filmizle/bilim-kurgu-filmleri-izle/" : "Bilim Kurgu",
        f"{main_url}/filmizle/draam-filmleri-izle/"       : "Dram",
        f"{main_url}/filmizle/gerilimm-filmleri-izle/"    : "Gerilim",
        f"{main_url}/filmizle/komedi-filmleri-izle-hd/"   : "Komedi",
        f"{main_url}/filmizle/korkuu-filmleri-izle/"      : "Korku",
        f"{main_url}/filmizle/macera-filmleri-izle-hd/"   : "Macera",
        f"{main_url}/filmizle/succ-filmleri-izle/"        : "Suç",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        full_url = f"{url.rstrip('/')}/page/{page}/" if page > 1 else url
        istek    = await self.async_cf_get(full_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movie-poster"):
            title  = veri.select_attr("img", "alt") or veri.select_attr("a", "title")
            href   = veri.select_attr("a", "href")
            img    = veri.select_first("img")
            poster = img.attrs.get("data-wpfc-original-src") or img.attrs.get("src") if img else None

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title.strip(),
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.async_cf_get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movie-poster"):
            title  = veri.select_attr("img", "alt") or veri.select_attr("a", "title")
            href   = veri.select_attr("a", "href")
            img    = veri.select_first("img")
            poster = img.attrs.get("data-wpfc-original-src") or img.attrs.get("src") if img else None

            if title and href:
                results.append(SearchResult(
                    title  = title.strip(),
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("h1.title") or secici.select_text("h1")
        poster      = secici.select_poster("img.cover-img") or secici.select_poster("img.poster-img")
        description = secici.select_text("div.movie-description") or secici.select_text("div.description-text")
        rating      = secici.select_text("span.average") or secici.regex_first(r"IMDb\s*:\s*([\d.]+)", secici.html)
        year        = secici.select_text("span.date a") or secici.regex_first(r"Vizyon Tarihi\s*:\s*(\d{4})", secici.html)
        actors      = secici.select_texts("div.cast-container a") or secici.select_texts("div.actors-grid .h6 a")
        tags        = secici.select_texts("div.categories-container-details a") or secici.select_texts("div.genre-container a")
        duration    = secici.extract_duration("Süre")

        # Dizi-Bölüm kontrolü
        episodes = []
        for link in secici.select("div.seasons-container a[href*='/bolum/']"):
            href = link.attrs.get("href")
            s, e = secici.extract_season_episode(href)
            if s and e:
                episodes.append(Episode(
                    season  = s,
                    episode = e,
                    title   = link.text(strip=True),
                    url     = self.fix_url(href)
                ))

        if episodes:
            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = title,
                description = description,
                tags        = tags,
                rating      = rating,
                year        = year,
                actors      = actors,
                episodes    = episodes
            )

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors,
            duration    = duration
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        response = []
        # Lazy load iframeler için data-wpfc-original-src veya src kontrolü
        for iframe in secici.select("iframe"):
            src = iframe.attrs.get("data-wpfc-original-src") or iframe.attrs.get("src")
            if not src or "google" in src or "youtube" in src or "fragman" in src.lower():
                continue

            data = await self.extract(self.fix_url(src), referer=url)
            self.collect_results(response, data)

        # Eğer hala link yoksa fragmanları (fragman olmayanları) tekrar zorla
        if not response:
            for iframe in secici.select("iframe"):
                src = iframe.attrs.get("data-wpfc-original-src") or iframe.attrs.get("src")
                if src and src.startswith("http"):
                    data = await self.extract(self.fix_url(src), referer=url)
                    self.collect_results(response, data)

        return response
