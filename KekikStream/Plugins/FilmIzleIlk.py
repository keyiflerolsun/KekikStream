# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
import base64, re

class FilmIzleIlk(PluginBase):
    name        = "FilmIzleIlk"
    language    = "tr"
    main_url    = "https://www.filmizleilk.fit"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "filmizleilk.biz Yerli ve Yabancı en son Film ve Dizileri Full HD 1080p Bluray Tek Part Full izle"

    main_page   = {
        f"{main_url}/page/"                          : "Son Filmler",
        f"{main_url}/film/aile-filmleri/page/"       : "Aile",
        f"{main_url}/film/aksiyon-filmleri/page/"    : "Aksiyon",
        f"{main_url}/film/animasyon-filmleri/page/"  : "Animasyon",
        f"{main_url}/film/bilimkurgu-filmleri/page/" : "Bilim Kurgu",
        f"{main_url}/film/dram-filmleri/page/"       : "Dram",
        f"{main_url}/film/fantastik-filmler/page/"   : "Fantastik",
        f"{main_url}/film/gerilim-filmleri/page/"    : "Gerilim",
        f"{main_url}/film/gizemli-filmler/page/"     : "Gizem",
        f"{main_url}/film/komedi-filmleri/page/"     : "Komedi",
        f"{main_url}/film/korku-filmleri/page/"      : "Korku",
        f"{main_url}/film/macera-filmleri/page/"     : "Macera",
        f"{main_url}/film/romantik-filmler/page/"    : "Romantik",
        f"{main_url}/film/savas-filmleri/page/"      : "Savaş",
        f"{main_url}/film/suc-filmleri/page/"        : "Suç",
        f"{main_url}/film/tarihi-filmler/page/"      : "Tarih",
        f"{main_url}/film/western-filmler/page/"     : "Western",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}{page}")
        secici = HTMLHelper(istek.text)

        selector = "div.home-con div.movie-box" if category == "Son Filmler" else "div.movie-box"

        results = []
        for veri in secici.select(selector):
            title  = veri.select_text("div.name a")
            href   = veri.select_attr("div.name a", "href")
            poster = veri.select_attr("div.img img", "src")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movie-box"):
            title  = veri.select_text("div.name a")
            href   = veri.select_attr("div.name a", "href")
            poster = veri.select_attr("div.img img", "src")

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

        title       = secici.select_text("div.film h1") or secici.select_text("h1.film")
        poster      = secici.select_attr("[property='og:image']", "content")
        description = secici.select_text("div.description")
        rating      = (secici.select_text("div.imdb-count") or "").split()[0] if secici.select_text("div.imdb-count") else None
        year        = secici.regex_first(r"(\d{4})", secici.select_text("li.release"))
        duration    = secici.regex_first(r"(\d+)", secici.select_text("li.time"))
        actors      = secici.select_texts("[href*='oyuncular']")

        if "/dizi/" in url:
            tags     = secici.select_texts("div.category a")
            episodes = []

            for veri in secici.select("div.episode-box"):
                ep_href = veri.select_attr("div.name a", "href")
                if not ep_href:
                    continue

                ssn_text = veri.select_text("span.episodetitle") or ""
                # "1. Sezon" kısmından sezon no çıkar
                ep_detail_el = veri.select_first("span.episodetitle b")
                ep_detail    = ep_detail_el.text(strip=True) if ep_detail_el else ""
                # ownText: sadece elemanın kendisinin metni (child hariç)
                ssn_own      = ssn_text.replace(ep_detail, "").strip()

                season  = int(ssn_own.split(".")[0]) if ssn_own and ssn_own[0].isdigit() else 1
                episode = int(ep_detail.split(".")[0]) if ep_detail and ep_detail[0].isdigit() else 1

                episodes.append(Episode(
                    season  = season,
                    episode = episode,
                    title   = f"{ssn_own} - {ep_detail}".strip(" -"),
                    url     = self.fix_url(ep_href),
                ))

            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = title,
                description = description,
                tags        = tags,
                year        = year,
                actors      = actors,
                rating      = rating,
                duration    = duration,
                episodes    = episodes,
            )

        tags = secici.select_texts("ul.post-categories a")
        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            year        = year,
            actors      = actors,
            rating      = rating,
            duration    = duration,
        )

    @staticmethod
    def _get_iframe_from_base64(source_code: str) -> str:
        """PHA+ base64 pattern — iframe çıkar."""
        match = re.search(r"PHA\+[0-9a-zA-Z+/=]*", source_code)
        if not match:
            return ""

        atob = match.group(0)
        # Padding ekle
        padding = 4 - len(atob) % 4
        if padding < 4:
            atob += "=" * padding

        try:
            decoded = base64.b64decode(atob).decode("utf-8")
            secici  = HTMLHelper(decoded)
            return secici.select_attr("iframe", "src") or ""
        except Exception:
            return ""

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        response = []
        iframes  = set()

        # Ana iframe
        main_frame = secici.select_attr("iframe", "src")
        if main_frame:
            iframes.add(self.fix_url(main_frame))

        # Alternatif linkler (div.parts-middle a)
        for link in secici.select("div.parts-middle a"):
            alt_href = link.attrs.get("href", "")
            if alt_href:
                try:
                    alt_resp   = await self.httpx.get(self.fix_url(alt_href))
                    alt_iframe = self._get_iframe_from_base64(alt_resp.text)
                    if alt_iframe:
                        iframes.add(self.fix_url(alt_iframe))
                except Exception:
                    pass

        async def _process_iframe(iframe_url):
            if "vidmoly" in iframe_url.lower():
                try:
                    i_resp  = await self.httpx.get(iframe_url, headers={"Referer": f"{self.main_url}/"})
                    m3u_url = HTMLHelper(i_resp.text).regex_first(r'file:"([^"]+)')
                    if m3u_url:
                        return ExtractResult(
                            name    = "VidMoly",
                            url     = m3u_url,
                            referer = "https://vidmoly.to/",
                        )
                except Exception:
                    pass
            return await self.extract(iframe_url, referer=f"{self.main_url}/")

        tasks = [_process_iframe(iframe) for iframe in iframes]
        for data in await self.gather_with_limit(tasks):
            self.collect_results(response, data)

        return response
