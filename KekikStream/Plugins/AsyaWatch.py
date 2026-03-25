# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re, json, base64

class AsyaWatch(PluginBase):
    name        = "AsyaWatch"
    language    = "tr"
    main_url    = "https://asyawatch.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Kore, Çin ve Japon dizilerini tek tıkla HD ve Türkçe altyazılı izle. En güncel Asya dizileri, BL seriler, unutulmaz Asya filmleri ve web dramalar seni bekliyor."

    main_page   = {
        f"{main_url}/tum-bolumler" : "Yeni Bölümler",
        "15"                       : "Aile",
        "9"                        : "Aksiyon",
        "5"                        : "Bilim Kurgu",
        "2"                        : "Dram",
        "12"                       : "Fantastik",
        "18"                       : "Gerilim",
        "3"                        : "Gizem",
        "8"                        : "Korku",
        "4"                        : "Komedi",
        "7"                        : "Romantik",
    }

    def _fix_poster(self, url: str) -> str:
        if not url:
            return ""
        url = re.sub(r"images-macellan-online\.cdn\.ampproject\.org/i/s/", "", url)
        url = url.replace("file.dizilla.club", "file.macellan.online")
        url = url.replace("images.dizilla.club", "images.macellan.online")
        url = url.replace("images.dizimia4.com", "images.macellan.online")
        url = url.replace("file.dizimia4.com", "file.macellan.online")
        url = url.replace("/f/f/", "/630/910/")
        url = re.sub(r"(file\.)\S+?/", r"\1macellan.online/", url)
        url = re.sub(r"(images\.)\S+?/", r"\1macellan.online/", url)
        return url

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        if "tum-bolumler" in url:
            istek  = await self.httpx.get(url)
            secici = HTMLHelper(istek.text)

            results = []
            for a_tag in secici.select("div.col-span-3 a"):
                name_el = a_tag.select_first("h2")
                name    = name_el.text(strip=True) if name_el else ""
                ep_el   = a_tag.select_first("div.opacity-80")
                ep_text = ep_el.text(strip=True) if ep_el else ""
                title   = f"{name} - {ep_text}" if name and ep_text else name

                href   = a_tag.select_attr(None, "href")
                poster = a_tag.select_attr("div.image img", "src")

                if title and href:
                    results.append(MainPageResult(
                        category = category,
                        title    = title,
                        url      = self.fix_url(href),
                        poster   = self.fix_url(poster),
                    ))
            return results

        # Kategori API
        api_url = f"{self.main_url}/api/bg/findSeries?releaseYearStart=1900&releaseYearEnd=2026&imdbPointMin=1&imdbPointMax=10&categoryIdsComma={url}&countryIdsComma=&orderType=date_desc&languageId=-1&currentPage={page}&currentPageCount=24&queryStr=&categorySlugsComma=&countryCodesComma="
        istek   = await self.httpx.post(
            api_url,
            headers = {
                "Accept"           : "application/json, text/plain, */*",
                "X-Requested-With" : "XMLHttpRequest",
                "Referer"          : f"{self.main_url}/",
            },
        )

        results = []
        try:
            data    = istek.json()
            encoded = data.get("response", "")
            decoded = base64.b64decode(encoded).decode("utf-8", errors="replace")
            media   = json.loads(decoded)

            for item in media.get("result", []):
                title  = item.get("original_title", "")
                href   = item.get("used_slug", "")
                poster = self._fix_poster(item.get("poster_url", ""))
                if title and href:
                    results.append(MainPageResult(
                        category = category,
                        title    = title,
                        url      = self.fix_url(href),
                        poster   = self.fix_url(poster),
                    ))
        except Exception:
            pass

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek = await self.httpx.post(
            f"{self.main_url}/api/bg/searchcontent?searchterm={query}",
            headers = {
                "Accept"           : "application/json, text/plain, */*",
                "X-Requested-With" : "XMLHttpRequest",
                "Referer"          : f"{self.main_url}/",
            },
        )

        results = []
        try:
            data    = istek.json()
            encoded = data.get("response", "")
            decoded = base64.b64decode(encoded).decode("utf-8", errors="replace")
            search  = json.loads(decoded)

            for item in search.get("result", []):
                title  = item.get("title") or item.get("object_name", "")
                href   = item.get("slug") or item.get("used_slug", "")
                poster = self._fix_poster(item.get("poster") or item.get("object_poster_url", ""))

                if href and "/seri-filmler/" in href:
                    continue

                if title and href:
                    results.append(SearchResult(
                        title  = title,
                        url    = self.fix_url(href),
                        poster = self.fix_url(poster),
                    ))
        except Exception:
            pass

        return results

    def _parse_secure_data(self, html: str) -> dict:
        """__NEXT_DATA__ scriptinden secureData'yı çöz"""
        secici = HTMLHelper(html)
        script = secici.select_first("script#__NEXT_DATA__")
        if not script:
            return {}
        try:
            next_data   = json.loads(script.text())
            secure_data = next_data["props"]["pageProps"]["secureData"]
            if isinstance(secure_data, str):
                secure_data = secure_data.strip('"')
            decoded     = base64.b64decode(secure_data).decode("utf-8", errors="replace")
            return json.loads(decoded)
        except Exception:
            return {}

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek = await self.async_cf_get(url)
        data  = self._parse_secure_data(istek.text)

        item        = data.get("contentItem", {})
        title       = item.get("original_title", "")
        poster      = self._fix_poster(item.get("poster_url", ""))
        description = item.get("description", "")
        year        = item.get("release_year")
        tags_str    = item.get("categories", "")
        tags        = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
        rating      = item.get("imdb_point", "")

        related = data.get("RelatedResults", {})

        actors    = []
        cast_data = related.get("getSerieCastsById", {}).get("result", [])
        if not cast_data:
            cast_data = related.get("getMovieCastsById", {}).get("result", [])

        for c in cast_data:
            if c.get("name"):
                actors.append(c["name"])

        # Dizi mi?
        series_data = related.get("getSerieSeasonAndEpisodes", {})
        if series_data:
            episodes = []
            for season in series_data.get("result", []):
                szn = season.get("season_no", 1)
                for ep in season.get("episodes", []):
                    ep_text = ep.get("episode_text", "")
                    ep_no   = ep.get("episode_no")
                    ep_slug = ep.get("used_slug", "")
                    if ep_slug:
                        episodes.append(Episode(
                            season  = szn,
                            episode = ep_no,
                            title   = ep_text or f"Bölüm {ep_no}",
                            url     = self.fix_url(ep_slug),
                        ))

            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = title,
                description = description,
                tags        = tags,
                year        = str(year) if year else None,
                rating      = str(rating) if rating else None,
                actors      = actors,
                episodes    = episodes,
            )

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            year        = str(year) if year else None,
            rating      = str(rating) if rating else None,
            actors      = actors,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek = await self.async_cf_get(url)
        data  = self._parse_secure_data(istek.text)

        related = data.get("RelatedResults", {})

        source_content = None

        if "/dizi/" in url or "/bolum/" in url:
            ep_sources = related.get("getEpisodeSources", {})
            if not ep_sources:
                 ep_sources = related.get("getEpisodeSourcesById", {})

            if ep_sources.get("state"):
                first = (ep_sources.get("result") or [None])[0]
                if first:
                    source_content = first.get("source_content", "")
        else:
            movie_parts = related.get("getMoviePartsById", {})
            if movie_parts.get("state"):
                first_part = (movie_parts.get("result") or [None])[0]
                if first_part:
                    part_id      = first_part.get("id")
                    src_key      = f"getMoviePartSourcesById_{part_id}"
                    part_sources = related.get(src_key, {})
                    first_src    = (part_sources.get("result") or [None])[0]
                    if first_src:
                        source_content = first_src.get("source_content", "")

        if not source_content:
            return []

        secici     = HTMLHelper(source_content)
        iframe_src = secici.select_attr("iframe", "src")
        if not iframe_src:
            return []

        iframe_src = self.fix_url(iframe_src)

        # sn.dplayer74.site → sn.hotlinger.com yönlendirme
        if "sn.dplayer74.site" in iframe_src:
            iframe_src = iframe_src.replace("sn.dplayer74.site", "sn.hotlinger.com")

        response    = []
        data_result = await self.extract(iframe_src, referer=f"{self.main_url}/")
        self.collect_results(response, data_result)

        return self.deduplicate(response)
