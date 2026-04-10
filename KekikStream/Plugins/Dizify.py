# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult
import re

class Dizify(PluginBase):
    name        = "Dizify"
    language    = "tr"
    main_url    = "https://dizify.org"
    api_url     = f"{main_url}/api/v1"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Dizify - Film ve Dizi İzle | HD Türkçe Altyazılı & Dublaj"

    # API endpoints for main page categories
    main_page   = {
        f"{api_url}/movies?type=trending" : "Trend Filmler",
        f"{api_url}/series?type=trending" : "Trend Diziler",
        f"{api_url}/movies?genres[]=1"    : "Aksiyon Filmleri",
        f"{api_url}/movies?genres[]=10"   : "Komedi Filmleri",
        f"{api_url}/movies?genres[]=5"    : "Korku Filmleri",
        f"{api_url}/movies?genres[]=2"    : "Bilim-Kurgu Filmleri",
    }

    # TMDB fallback for missing metadata
    tmdb_api = "https://api.themoviedb.org/3"
    tmdb_key = "1865f43a0549ca50d341dd9ab8b29f49"

    async def _get_tmdb_metadata(self, tmdb_id: int | str | None, item_type: str) -> dict:
        if not tmdb_id:
            return {}

        media_type = "movie" if item_type == "movie" else "tv"
        try:
            resp = await self.httpx.get(
                f"{self.tmdb_api}/{media_type}/{tmdb_id}",
                params={
                    "api_key"            : self.tmdb_key,
                    "language"           : "tr-TR",
                    "append_to_response" : "credits"
                }
            )
            return resp.json() if resp.status_code == 200 else {}
        except Exception:
            return {}

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        params = {"page": page}
        istek  = await self.httpx.get(url, params=params)
        data   = istek.json()

        if not data.get("success"):
            return []

        results = []
        items   = data.get("data", [])
        # Sometimes paginated responses have items inside another 'data' key
        if isinstance(items, dict):
            items = items.get("data", [])

        for item in items:
            results.append(MainPageResult(
                category = category,
                title    = item["title"],
                url      = self.fix_url(item["url"]),
                poster   = self.fix_url(item["poster_url"]),
            ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek = await self.httpx.get(f"{self.api_url}/search", params={"q": query})
        data  = istek.json()

        if not data.get("success"):
            return []

        results     = []
        search_data = data.get("data", {})

        # Merge movies and series
        movies = search_data.get("movies", [])
        series = search_data.get("series", [])

        for item in movies + series:
            results.append(SearchResult(
                title  = item["title"],
                url    = self.fix_url(item["url"]),
                poster = self.fix_url(item["poster_url"]),
            ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        # Determine slug from URL using regex
        is_series = "dizi-izle" in url or "series" in url

        if is_series:
            # Match /dizi-izle/slug or /series/slug
            match    = re.search(r'/(?:dizi-izle|series)/([^/]+)', url)
            slug     = match.group(1) if match else url.rstrip("/").split("/")[-1]
            endpoint = f"{self.api_url}/series/{slug}"
        else:
            # Match /film-izle/slug or /movies/slug
            match    = re.search(r'/(?:film-izle|movies)/([^/]+)', url)
            slug     = match.group(1) if match else url.rstrip("/").split("/")[-1]
            endpoint = f"{self.api_url}/movies/{slug}"

        istek = await self.httpx.get(endpoint)
        data  = istek.json()

        # Fallback between movie/series if first guess fails
        if not data.get("success"):
            alt_endpoint = f"{self.api_url}/movies/{slug}" if is_series else f"{self.api_url}/series/{slug}"
            istek        = await self.httpx.get(alt_endpoint)
            data         = istek.json()
            if data.get("success"):
                is_series = not is_series

        if not data.get("success"):
            return MovieInfo(url=url, title="Hata: Veri Alınamadı")

        item = data.get("data", {})

        # Fetch TMDB metadata for missing info (cast, duration)
        tmdb_id   = item.get("tmdb_id")
        item_type = "series" if is_series else "movie"
        tmdb_meta = await self._get_tmdb_metadata(tmdb_id, "movie" if not is_series else "series")

        # Extract actors and duration from TMDB if available
        actors   = [c["name"] for c in tmdb_meta.get("credits", {}).get("cast", [])][:10]
        duration = item.get("runtime") or item.get("runtime_avg") or tmdb_meta.get("runtime")
        if not duration and is_series:
            runtimes = tmdb_meta.get("episode_run_time") or []
            duration = runtimes[0] if runtimes else None

        # Common metadata
        common_info = {
            "url"         : url,
            "poster"      : self.fix_url(item.get("poster_url")),
            "title"       : item.get("title"),
            "description" : item.get("description") or item.get("short_description"),
            "year"        : str(item.get("release_year") or ""),
            "rating"      : str(item.get("tmdb_rating") or item.get("imdb_rating") or ""),
            "tags"        : [g["name"] for g in item.get("genres", [])],
            "actors"      : actors if actors else [c["name"] for c in item.get("cast", [])],
            "duration"    : duration,
        }

        # Clean actors if list is empty
        if not common_info["actors"]:
            common_info["actors"] = None
        elif isinstance(common_info["actors"], list):
            common_info["actors"] = ", ".join(common_info["actors"])

        if is_series:
            episodes = []
            for season in item.get("seasons", []):
                s_num = season.get("season_number")
                for ep in season.get("episodes", []):
                    # We store the source API URL in the episode URL for load_links
                    ep_api_url = f"{self.api_url}/episodes/{ep['id']}/sources"
                    ep_title   = ep.get("title") or f"{s_num}. Sezon {ep.get('episode_number')}. Bölüm"
                    episodes.append(Episode(
                        season  = s_num,
                        episode = ep.get("episode_number"),
                        title   = ep_title,
                        url     = ep_api_url,
                    ))
            return SeriesInfo(**common_info, episodes=episodes)

        # For movies, we return the sources API URL as the item URL for load_links
        sources_url = f"{self.api_url}/movies/{item['id']}/sources"
        common_info["url"] = sources_url
        return MovieInfo(**common_info)

    async def load_links(self, url: str) -> list[ExtractResult]:
        # If url is already an API source endpoint (from our load_item)
        if "/sources" in url:
            istek = await self.httpx.get(url)
            data  = istek.json()
            if not data.get("success"):
                return []

            results = []
            for src in data.get("data", []):
                embed_url = src.get("url")
                if not embed_url:
                    continue

                label   = src.get("label") or src.get("audio_type", "Kaynak")
                quality = src.get("quality") or ""

                # Use the built-in extract method which finds the right extractor
                res = await self.extract(embed_url, prefix=f"{label} {quality}".strip())
                self.collect_results(results, res)

            return results

        # Fallback for standard URLs (try to resolve to sources via API)
        is_series = "dizi-izle" in url or "series" in url
        if is_series:
            match = re.search(r'/(?:dizi-izle|series)/([^/]+)', url)
            slug  = match.group(1) if match else url.rstrip("/").split("/")[-1]
            istek = await self.httpx.get(f"{self.api_url}/series/{slug}")
        else:
            match = re.search(r'/(?:film-izle|movies)/([^/]+)', url)
            slug  = match.group(1) if match else url.rstrip("/").split("/")[-1]
            istek = await self.httpx.get(f"{self.api_url}/movies/{slug}")

        data = istek.json()
        if data.get("success"):
            item_id = data["data"]["id"]
            if is_series:
                 # Series sources are usually per episode, but if we have a series URL we can't guess the episode
                 # This part might need more logic if we want to support series root URLs in load_links
                 return []
            return await self.load_links(f"{self.api_url}/movies/{item_id}/sources")

        return []
