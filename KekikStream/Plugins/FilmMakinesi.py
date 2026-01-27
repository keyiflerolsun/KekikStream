# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper

class FilmMakinesi(PluginBase):
    name        = "FilmMakinesi"
    language    = "tr"
    main_url    = "https://filmmakinesi.to"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Film Makinesi ile en yeni ve güncel filmleri Full HD kalite farkı ile izleyebilirsiniz. Film izle denildiğinde akla gelen en kaliteli film sitesi."

    main_page   = {
        f"{main_url}/filmler-1/"                : "Son Filmler",
        f"{main_url}/tur/aksiyon-fm1/film/"     : "Aksiyon",
        f"{main_url}/tur/aile-fm1/film/"        : "Aile",
        f"{main_url}/tur/animasyon-fm2/film/"   : "Animasyon",
        f"{main_url}/tur/belgesel/film/"        : "Belgesel",
        f"{main_url}/tur/biyografi/film/"       : "Biyografi",
        f"{main_url}/tur/bilim-kurgu-fm3/film/" : "Bilim Kurgu",
        f"{main_url}/tur/dram-fm1/film/"        : "Dram",
        f"{main_url}/tur/fantastik-fm1/film/"   : "Fantastik",
        f"{main_url}/tur/gerilim-fm1/film/"     : "Gerilim",
        f"{main_url}/tur/gizem/film/"           : "Gizem",
        f"{main_url}/tur/komedi-fm1/film/"      : "Komedi",
        f"{main_url}/tur/korku-fm1/film/"       : "Korku",
        f"{main_url}/tur/macera-fm1/film/"      : "Macera",
        f"{main_url}/tur/muzik/film/"           : "Müzik",
        f"{main_url}/tur/polisiye/film/"        : "Polisiye",
        f"{main_url}/tur/romantik-fm1/film/"    : "Romantik",
        f"{main_url}/tur/savas-fm1/film/"       : "Savaş",
        f"{main_url}/tur/spor/film/"            : "Spor",
        f"{main_url}/tur/tarih/film/"           : "Tarih",
        f"{main_url}/tur/western-fm1/film/"     : "Western"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = self.cloudscraper.get(f"{url}{'' if page == 1 else f'page/{page}/'}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.item-relative"):
            title  = secici.select_text("div.title", veri)
            href   = secici.select_attr("a", "href", veri)
            poster = secici.select_poster("img", veri)

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/arama/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for article in secici.select("div.item-relative"):
            title  = secici.select_text("div.title", article)
            href   = secici.select_attr("a", "href", article)
            poster = secici.select_poster("img", article)

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = self.clean_title(secici.select_text("h1.title"))
        poster      = secici.select_poster("img.cover-img")
        description = secici.select_text("div.info-description p")
        rating      = secici.select_text("div.info div.imdb b")
        year        = secici.select_text("span.date a")
        actors      = secici.select_texts("div.cast-name")
        tags        = secici.select_texts("div.type a[href*='/tur/']")
        duration    = secici.regex_first(r"(\d+)", secici.select_text("div.time"))

        episodes = []
        for link in secici.select("a[href]"):
            href = link.attrs.get("href", "")
            s, e = secici.extract_season_episode(href)
            if s and e:
                name = link.text(strip=True).split("Bölüm")[-1].strip() if "Bölüm" in link.text() else ""
                episodes.append(Episode(
                    season  = s,
                    episode = e,
                    title   = name,
                    url     = self.fix_url(href)
                ))

        # Tekrar edenleri temizle ve sırala
        if episodes:
            seen = set()
            unique = []
            for ep in episodes:
                if (ep.season, ep.episode) not in seen:
                    seen.add((ep.season, ep.episode))
                    unique.append(ep)
            unique.sort(key=lambda x: (x.season or 0, x.episode or 0))

            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = title,
                description = description,
                tags        = tags,
                rating      = rating,
                year        = year,
                actors      = actors,
                duration    = duration,
                episodes    = unique
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
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        response    = []
        shared_subs = []

        # Video parts linklerini ve etiketlerini al
        for link in secici.select("div.video-parts a[data-video_url]"):
            video_url = link.attrs.get("data-video_url")
            label     = link.text(strip=True) if link.text(strip=True) else ""

            if video_url:
                data = await self.extract(video_url, prefix=label.split()[0] if label else None)
                if data:
                    if isinstance(data, list):
                        for d in data:
                            response.append(d)
                            if d.subtitles:
                                shared_subs.extend(d.subtitles)
                    else:
                        response.append(data)
                        if data.subtitles:
                            shared_subs.extend(data.subtitles)

        # Eğer video-parts yoksa iframe kullan
        if not response:
            iframe_src = secici.select_attr("iframe", "data-src")
            if iframe_src:
                data = await self.extract(iframe_src)
                if data:
                    if isinstance(data, list):
                        for d in data:
                            response.append(d)
                            if d.subtitles:
                                shared_subs.extend(d.subtitles)
                    else:
                        response.append(data)
                        if data.subtitles:
                            shared_subs.extend(data.subtitles)

        # Altyazıları Dağıt
        if shared_subs:
            unique_subs = []
            seen_urls   = set()
            for sub in shared_subs:
                if sub.url not in seen_urls:
                    seen_urls.add(sub.url)
                    unique_subs.append(sub)

            for res in response:
                current_urls = {s.url for s in res.subtitles}
                for sub in unique_subs:
                    if sub.url not in current_urls:
                        res.subtitles.append(sub)

        return response
