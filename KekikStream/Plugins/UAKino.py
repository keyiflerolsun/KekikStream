# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re


class UAKino(PluginBase):
    name        = "UAKino"
    language    = "uk"
    main_url    = "https://uakino.best"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Дивитися фільми та серіали онлайн в HD якості. У нас можна дивитися кіно онлайн безкоштовно, у високій якості та з якісним українським дубляжем"

    main_page = {
        f"{main_url}/filmy/page/"                 : "Фільми",
        f"{main_url}/filmy/genre-action/page/"    : "Бойовики",
        f"{main_url}/filmy/genre_fantastic/page/" : "Фантастика",
        f"{main_url}/filmy/genre_adventure/page/" : "Пригоди",
        f"{main_url}/filmy/genre_comedy/page/"    : "Комедії",
        f"{main_url}/filmy/genre_detective/page/" : "Детективи",
        f"{main_url}/filmy/genre_drama/page/"    : "Драми",
        f"{main_url}/filmy/genre_horror/page/"    : "Жахи",
        f"{main_url}/filmy/genre_thriller/page/"  : "Трилери",
        f"{main_url}/seriesss/page/"              : "Серіали",
        f"{main_url}/seriesss/doramy/page/"       : "Дорами",
        f"{main_url}/seriesss/comedy_series/page/": "Комедійні серіали",
        f"{main_url}/seriesss/drama_series/page/" : "Драматичні серіали",
        f"{main_url}/animeukr/page/"              : "Аніме",
        f"{main_url}/cartoon/page/"               : "Мультфільми",
        f"{main_url}/cartoon/cartoonseries/page/" : "Мультсеріали"
    }

    def _fix_file_url(self, url: str) -> str:
        """Protokol-bağıl ve eksik şema düzeltmesi."""
        if url.startswith("//"):
            return f"https:{url}"
        if "/vod/" in url and not url.startswith("http"):
            return f"https://ashdi.vip{url}"
        return url

    async def _fetch_playlist(self, news_id: str, xfname: str, edittime: str) -> str | None:
        """AJAX playlist HTML'ini getirir."""
        istek = await self.httpx.get(
            url     = f"{self.main_url}/engine/ajax/playlists.php",
            params  = {"news_id": news_id, "xfield": xfname, "time": edittime},
            headers = {"X-Requested-With": "XMLHttpRequest"},
        )
        veri = istek.json()
        return veri.get("response") if veri.get("success") else None

    def _parse_playlist_items(self, html: str) -> list[dict]:
        """Playlist HTML'den [{file, name, voice, data_id}] listesi döndürür."""
        secici = HTMLHelper(html)
        sonuc  = []
        for li in secici.select("ul > li"):
            dosya = li.select_attr(None, "data-file")
            if not dosya:
                continue
            sonuc.append({
                "file"    : self._fix_file_url(dosya),
                "name"    : li.text().strip(),
                "voice"   : li.select_attr(None, "data-voice") or "",
                "data_id" : li.select_attr(None, "data-id") or "",
            })
        return sonuc

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}{page}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.owl-item, div.movie-item"):
            results.append(MainPageResult(
                category = category,
                title    = veri.select_text("a.movie-title"),
                url      = self.fix_url(veri.select_attr("a.movie-title", "href")),
                poster   = self.fix_url(veri.select_attr("img", "src")),
            ))
        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek = await self.httpx.post(
            url  = self.main_url,
            data = {"do": "search", "subaction": "search", "story": query.replace(" ", "+")},
        )
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movie-item.short-item"):
            results.append(SearchResult(
                title  = veri.select_text("a.movie-title"),
                url    = self.fix_url(veri.select_attr("a.movie-title", "href")),
                poster = self.fix_url(veri.select_attr("img", "src")),
            ))
        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title  = secici.select_text("h1 span.solototle") or secici.select_text("h1")
        poster = self.fix_url(secici.select_attr("div.film-poster img", "src"))
        desc   = secici.select_text("div[itemprop=description]")
        tags   = [a.text().strip() for a in secici.select("div.film-info > div:nth-child(4) a")]
        year   = secici.select_text("div.film-info > div:nth-child(2) a") or secici.regex_first(r"Рік виходу.*?(\d{4})")
        rating = (secici.select_text("div.film-info > div:nth-child(8) div.fi-desc") or "").split("/")[0].strip()
        actors = [a.text().strip() for a in secici.select("div.film-info > div:nth-child(6) a")]

        is_series = bool(re.search(r"(/anime-series)|(/seriesss)|(/cartoonseries)", url))

        if is_series:
            news_id  = secici.regex_first(r"news_id\s*=\s*'(\d+)'") or url.split("/")[-1].split("-")[0]
            edittime = secici.regex_first(r"dle_edittime\s*=\s*'(\d+)'") or "0"
            xfname   = secici.select_attr("div.playlists-ajax", "data-xfname") or "playlist"

            playlist_html = await self._fetch_playlist(news_id, xfname, edittime)
            episodes      = []

            if playlist_html:
                items = self._parse_playlist_items(playlist_html)

                # İlk ses grubu (voice) bölümlerini al
                first_id = None
                for item in items:
                    if first_id is None:
                        first_id = item["data_id"]
                    if item["data_id"] != first_id:
                        continue

                    sn, en = secici.extract_season_episode(item["name"])
                    episodes.append(Episode(
                        season  = sn or 1,
                        episode = en or (len(episodes) + 1),
                        title   = item["name"],
                        url     = item["file"],
                    ))

            return SeriesInfo(
                url         = url,
                poster      = poster,
                title       = title,
                description = desc,
                tags        = tags,
                rating      = rating,
                year        = year,
                actors      = actors,
                episodes    = episodes,
            )

        # Film
        return MovieInfo(
            url         = url,
            poster      = poster,
            title       = title,
            description = desc,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        results = []

        if not url.startswith("http"):
            return results

        # Doğrudan stream dosyası
        if any(ext in url for ext in [".mp4", ".m3u8"]):
            return [ExtractResult(name=self.name, url=url)]

        # ashdi.vip → Ashdi extractor'a gönder; başarısız olursa atla
        if "ashdi.vip" in url:
            ext = await self.extract(url, referer=f"{self.main_url}/")
            if ext:
                self.collect_results(results, ext)
            return results

        # Uakino sayfası → AJAX ile playlist al
        istek    = await self.httpx.get(url)
        secici   = HTMLHelper(istek.text)
        news_id  = secici.regex_first(r"news_id\s*=\s*'(\d+)'") or url.split("/")[-1].split("-")[0]
        edittime = secici.regex_first(r"dle_edittime\s*=\s*'(\d+)'") or "0"
        xfname   = secici.select_attr("div.playlists-ajax", "data-xfname") or "playlist"

        playlist_html = await self._fetch_playlist(news_id, xfname, edittime)
        if playlist_html:
            items = self._parse_playlist_items(playlist_html)
            tasks = [
                self.extract(item["file"], referer=f"{self.main_url}/", name_override=item['voice'] if item["voice"] else None)
                for item in items
            ]
            for item, ext in zip(items, await self.gather_with_limit(tasks), strict=False):
                if ext:
                    self.collect_results(results, ext)
                else:
                    results.append(ExtractResult(
                        name    = item['voice'] if item["voice"] else "Kaynak",
                        url     = item["file"],
                        referer = f"{self.main_url}/",
                    ))

        # iframe#pre fallback
        if not results:
            iframe_src = secici.select_attr("iframe#pre", "src") or secici.select_attr("iframe#pre", "data-src")
            if iframe_src:
                iframe_src = self._fix_file_url(iframe_src)
                ext        = await self.extract(iframe_src, referer=url)
                if ext:
                    self.collect_results(results, ext)

        if not results:
            if trailer_url := secici.regex_first(r"https://www\.youtube\.com/embed/[A-Za-z0-9_-]+", istek.text):
                results.append(ExtractResult(
                    name    = "Fragman",
                    url     = trailer_url,
                    referer = url,
                ))

        return results
