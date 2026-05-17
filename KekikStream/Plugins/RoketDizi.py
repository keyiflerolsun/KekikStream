# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, MovieInfo, Episode, ExtractResult, HTMLHelper
import base64, json, re

class RoketDizi(PluginBase):
    name        = "RoketDizi"
    language    = "tr"
    main_url    = "https://roketdizi.to"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Türkiye'nin en tatlış yabancı dizi izleme sitesi. Türkçe dublaj, altyazılı, eski ve yeni yabancı dizilerin yanı sıra kore (asya) dizileri izleyebilirsiniz."

    main_page = {
       f"{main_url}/dizi/tur/aksiyon"       : "Aksiyon",
       f"{main_url}/dizi/tur/animasyon"     : "Animasyon",
       f"{main_url}/dizi/tur/belgesel"      : "Belgesel",
       f"{main_url}/dizi/tur/bilim-kurgu"   : "Bilim Kurgu",
       f"{main_url}/dizi/tur/dram"          : "Dram",
       f"{main_url}/dizi/tur/fantastik"     : "Fantastik",
       f"{main_url}/dizi/tur/gerilim"       : "Gerilim",
       f"{main_url}/dizi/tur/gizem"         : "Gizem",
       f"{main_url}/dizi/tur/komedi"        : "Komedi",
       f"{main_url}/dizi/tur/kore-dizileri" : "Kore Dizileri",
       f"{main_url}/dizi/tur/korku"         : "Korku",
       f"{main_url}/dizi/tur/macera"        : "Macera",
       f"{main_url}/dizi/tur/romantik"      : "Romantik",
       f"{main_url}/dizi/tur/suc"           : "Suç",
       f"{main_url}/dizi/tur/tarih"         : "Tarih",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        full_url = f"{url}?page={page}" if page > 1 else url
        istek    = await self.async_cf_get(full_url)

        # Next.js verisini ayıkla
        match = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', istek.text, re.S)
        if match:
            try:
                data       = json.loads(match.group(1))
                secure_raw = data.get("props", {}).get("pageProps", {}).get("secureData")
                if secure_raw:
                    if isinstance(secure_raw, str):
                        secure_raw = secure_raw.strip('"')
                    decoded = json.loads(base64.b64decode(secure_raw).decode('utf-8', errors='ignore'))

                    results = []
                    # Farklı anahtarları kontrol et (getEpisodesOnBrandAll, content, vs.)
                    content_list = []
                    for key in ["getEpisodesOnBrandAll", "getEpisodesOnNewSeries", "getLastSeriesAll", "getMovieListByList"]:
                        val = decoded.get(key, {})
                        if isinstance(val, dict) and val.get("result"):
                            content_list = val["result"]
                            break

                    if not content_list:
                        # Fallback to search-like result if list empty
                        content_list = decoded.get("content", {}).get("result", [])

                    for item in content_list:
                        title  = item.get("object_name") or item.get("original_title") or item.get("culture_title")
                        slug   = item.get("used_slug")
                        poster = item.get("object_poster_url") or item.get("poster_url") or item.get("face_url")

                        if title and slug:
                            results.append(MainPageResult(
                                category = category,
                                title    = title.strip(),
                                url      = self.fix_url(f"{self.main_url}/{slug}"),
                                poster   = self.fix_url(poster)
                            ))
                    if results:
                        return results
            except Exception:
                pass

        # Fallback to HTML parsing
        secici  = HTMLHelper(istek.text)
        results = []
        for item in secici.select("div.new-added-list > span, div.film-card"):
            title  = item.select_text("span.line-clamp-1") or item.select_text("h2.card-title")
            href   = item.select_attr("a", "href")
            poster = item.select_attr("img", "src") or item.select_attr("img", "data-src")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title.strip(),
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster)
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        # RoketDizi search API POST gerektiriyor
        istek = await self.async_cf_post(
            url     = f"{self.main_url}/api/bg/searchContent?searchterm={query}",
            headers = {
                "Accept"           : "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With" : "XMLHttpRequest",
                "Referer"          : f"{self.main_url}/",
            }
        )

        try:
            veri    = istek.json()
            encoded = veri.get("response", "")
            if not encoded:
                return []

            decoded = json.loads(base64.b64decode(encoded).decode("utf-8", errors='ignore'))
            if not decoded.get("state"):
                return []

            results = []
            for item in decoded.get("result", []):
                title  = item.get("object_name", "")
                slug   = item.get("used_slug", "")
                poster = item.get("object_poster_url", "")

                if title and slug:
                    results.append(SearchResult(
                        title  = title.strip(),
                        url    = self.fix_url(f"{self.main_url}/{slug}"),
                        poster = self.fix_url(poster)
                    ))
            return results
        except Exception:
            return []

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek = await self.async_cf_get(url)

        match = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', istek.text, re.S)
        if not match:
            return SeriesInfo(url=url, title="Bilinmeyen")

        try:
            data       = json.loads(match.group(1))
            secure_raw = data.get("props", {}).get("pageProps", {}).get("secureData")
            if not secure_raw:
                 return SeriesInfo(url=url, title="Bilinmeyen (No Data)")

            if isinstance(secure_raw, str):
                secure_raw = secure_raw.strip('"')
            decoded = json.loads(base64.b64decode(secure_raw).decode('utf-8', errors='ignore'))

            content_item    = decoded.get("contentItem", {})
            related_results = decoded.get("RelatedResults", {})

            title       = content_item.get("original_title") or content_item.get("culture_title")
            poster      = content_item.get("poster_url") or content_item.get("face_url")
            description = content_item.get("description")
            rating      = str(content_item.get("imdb_point") or "")
            year        = str(content_item.get("release_year") or "")
            tags        = content_item.get("categories", "").split(",")

            actors     = []
            casts_data = related_results.get("getSerieCastsById") or related_results.get("getMovieCastsById") or related_results.get("getMovieSeriesPopularCasts")
            if casts_data and isinstance(casts_data, dict) and casts_data.get("result"):
                actors = [cast.get("name") for cast in casts_data["result"] if cast.get("name")]

            # Episodes extraction from secureData
            episodes     = []
            seasons_data = related_results.get("getSerieSeasonAndEpisodes", {})
            if seasons_data and seasons_data.get("result"):
                for season_obj in seasons_data["result"]:
                    s_num = season_obj.get("season_no", 1)
                    for ep_obj in season_obj.get("episodes", []):
                        e_num  = ep_obj.get("episode_no", 1)
                        e_slug = ep_obj.get("used_slug")
                        e_name = ep_obj.get("episode_text")
                        if e_slug:
                            episodes.append(Episode(
                                season  = s_num,
                                episode = e_num,
                                title   = e_name or f"{s_num}. Sezon {e_num}. Bölüm",
                                url     = self.fix_url(f"{self.main_url}/{e_slug}")
                            ))

            if episodes:
                episodes.sort(key=lambda x: (x.season, x.episode))
                return SeriesInfo(
                    url         = url,
                    poster      = self.fix_url(poster),
                    title       = title.strip(),
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
                title       = title.strip(),
                description = description,
                tags        = tags,
                rating      = rating,
                year        = year,
                actors      = actors
            )
        except Exception:
             return SeriesInfo(url=url, title="Hata (Parse)")

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek = await self.async_cf_get(url)

        match = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', istek.text, re.S)
        if not match:
            return []

        try:
            data       = json.loads(match.group(1))
            secure_raw = data.get("props", {}).get("pageProps", {}).get("secureData")
            if not secure_raw:
                return []

            if isinstance(secure_raw, str):
                secure_raw = secure_raw.strip('"')
            decoded = json.loads(base64.b64decode(secure_raw).decode('utf-8', errors='ignore'))

            # Look for sources in RelatedResults
            related     = decoded.get("RelatedResults", {})
            sources_obj = related.get("getEpisodeSources") or related.get("getMovieSources") or related.get("getEpisodeSourcesById")
            sources     = sources_obj.get("result", []) if isinstance(sources_obj, dict) else []

            results = []
            tasks   = []
            for src in sources:
                content = src.get("source_content", "")
                iframe  = HTMLHelper(content).select_attr("iframe", "src")
                if iframe:
                    tasks.append(self.extract(self.fix_url(iframe), referer=f"{self.main_url}/"))

            for res in await self.gather_with_limit(tasks):
                self.collect_results(results, res)

            return results
        except Exception:
            return []
