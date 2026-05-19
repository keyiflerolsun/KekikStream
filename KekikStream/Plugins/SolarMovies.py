# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult
import urllib.parse
import re

class SolarMovies(PluginBase):
    name        = "SolarMovies"
    language    = "en"
    main_url    = "https://solarmoviesz.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Solarmovies is the best free streaming site to watch movies and TV shows online in HD quality. Watch thousands of movies, TV series, anime without registration or payment. Solarmoviesz.com offers unlimited entertainment with latest movies and trending TV shows."

    tmdb_key = "56794302374630666ef844d447387b4a"
    tmdb_api = "https://api.themoviedb.org/3"

    main_page   = {
        "trending_movies" : "Trending Movies",
        "trending_tv"     : "Trending TV Shows",
        "popular_movies"  : "Popular Movies",
        "popular_tv"      : "Popular TV Shows",
        "action"          : "Action",
        "adventure"       : "Adventure",
        "animation"       : "Animation",
        "comedy"          : "Comedy",
        "crime"           : "Crime",
        "documentary"     : "Documentary",
        "drama"           : "Drama",
        "family"          : "Family",
        "fantasy"         : "Fantasy",
        "history"         : "History",
        "horror"          : "Horror",
        "music"           : "Music",
        "mystery"         : "Mystery",
        "romance"         : "Romance",
        "sci_fi"          : "Science Fiction",
        "tv_movie"        : "TV Movie",
        "thriller"        : "Thriller",
        "war"             : "War",
        "western"         : "Western"
    }

    genre_mapping = {
        "action"      : 28,
        "adventure"   : 12,
        "animation"   : 16,
        "comedy"      : 35,
        "crime"       : 80,
        "documentary" : 99,
        "drama"       : 18,
        "family"      : 10751,
        "fantasy"     : 14,
        "history"     : 36,
        "horror"      : 27,
        "music"       : 10402,
        "mystery"     : 9648,
        "romance"     : 10749,
        "sci_fi"      : 878,
        "tv_movie"    : 10770,
        "thriller"    : 53,
        "war"         : 10752,
        "western"     : 37
    }

    server_patterns = {
        "VidCore" : {
            "movie"   : "https://vidcore.net/movie/",
            "tv"      : "https://vidcore.net/tv/"
        },
        "EmbedMaster" : {
            "movie"       : "https://embedmaster.link/movie/",
            "tv"          : "https://embedmaster.link/tv/"
        },
        "VidEasy" : {
            "movie"   : "https://player.videasy.net/movie/",
            "tv"      : "https://player.videasy.net/tv/"
        },
        "VidFast" : {
            "movie"   : "https://vidfast.pro/movie/",
            "tv"      : "https://vidfast.pro/tv/"
        },
        "VidSrcEmbed" : {
            "movie"       : "https://vidsrc-embed.ru/embed/movie/",
            "tv"          : "https://vidsrc-embed.ru/embed/tv/"
        },
        "Vidify" : {
            "movie"  : "https://player.vidify.top/embed/movie/",
            "tv"     : "https://player.vidify.top/embed/tv/"
        }
    }

    async def _ensure_config(self):
        if hasattr(self, "_config_loaded") and self._config_loaded:
            return

        try:
            resp = await self.httpx.get(f"{self.main_url}/config.js")
            if resp.status_code == 200:
                text      = resp.text
                key_match = re.search(r"TMDB_API_KEY\s*:\s*['\"]([^'\"]+)['\"]", text)
                url_match = re.search(r"TMDB_BASE_URL\s*:\s*['\"]([^'\"]+)['\"]", text)
                if key_match:
                    self.tmdb_key = key_match.group(1)
                if url_match:
                    self.tmdb_api = url_match.group(1).rstrip("/")
        except Exception:
            pass

        self._config_loaded = True

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        await self._ensure_config()

        params = {
            "api_key" : self.tmdb_key,
            "page"    : page
        }

        media_type = "movie"

        if url == "trending_movies":
            api_endpoint = f"{self.tmdb_api}/trending/movie/week"
        elif url == "trending_tv":
            api_endpoint = f"{self.tmdb_api}/trending/tv/week"
            media_type   = "tv"
        elif url == "popular_movies":
            api_endpoint = f"{self.tmdb_api}/movie/popular"
        elif url == "popular_tv":
            api_endpoint = f"{self.tmdb_api}/tv/popular"
            media_type   = "tv"
        elif url in self.genre_mapping:
            api_endpoint = f"{self.tmdb_api}/discover/movie"
            params["with_genres"] = self.genre_mapping[url]
            params["sort_by"]     = "popularity.desc"
        else:
            return []

        try:
            resp = await self.httpx.get(
                api_endpoint,
                params  = params,
                headers = {"Referer": f"{self.main_url}/"}
            )
            if resp.status_code != 200:
                return []

            data    = resp.json().get("results", [])
            results = []
            for item in data:
                title       = item.get("title") or item.get("name")
                poster_path = item.get("poster_path")
                tmdb_id     = item.get("id")

                item_media_type = media_type
                if "media_type" in item:
                    item_media_type = item["media_type"]

                if title and tmdb_id:
                    results.append(MainPageResult(
                        category = category,
                        title    = title,
                        url      = f"https://solarmoviesz.com/details.html?id={tmdb_id}&type={item_media_type}",
                        poster   = f"https://image.tmdb.org/t/p/w300{poster_path}" if poster_path else ""
                    ))
            return results
        except Exception:
            return []

    async def search(self, query: str) -> list[SearchResult]:
        await self._ensure_config()

        try:
            resp = await self.httpx.get(
                f"{self.tmdb_api}/search/multi",
                params  = {
                    "api_key" : self.tmdb_key,
                    "query"   : query,
                    "page"    : 1
                },
                headers = {"Referer": f"{self.main_url}/"}
            )
            if resp.status_code != 200:
                return []

            data    = resp.json().get("results", [])
            results = []
            for item in data:
                media_type = item.get("media_type")
                if media_type not in ["movie", "tv"]:
                    continue

                title       = item.get("title") or item.get("name")
                poster_path = item.get("poster_path")
                tmdb_id     = item.get("id")

                if title and tmdb_id:
                    results.append(SearchResult(
                        title  = title,
                        url    = f"https://solarmoviesz.com/details.html?id={tmdb_id}&type={media_type}",
                        poster = f"https://image.tmdb.org/t/p/w300{poster_path}" if poster_path else ""
                    ))
            return results
        except Exception:
            return []

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        await self._ensure_config()

        parsed    = urllib.parse.urlparse(url)
        params    = urllib.parse.parse_qs(parsed.query)
        tmdb_id   = params.get("id", [""])[0]
        item_type = params.get("type", ["movie"])[0]

        if not tmdb_id:
            raise ValueError("TMDB ID not found in URL")

        resp = await self.httpx.get(
            f"{self.tmdb_api}/{item_type}/{tmdb_id}",
            params  = {
                "api_key"            : self.tmdb_key,
                "append_to_response" : "credits"
            },
            headers = {"Referer": f"{self.main_url}/"}
        )
        if resp.status_code != 200:
            raise ValueError(f"Failed to fetch TMDB details, status: {resp.status_code}")

        data = resp.json()

        title       = data.get("title") or data.get("name") or ""
        poster_path = data.get("poster_path")
        poster      = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else ""
        description = data.get("overview") or ""

        release_date = data.get("release_date") or data.get("first_air_date") or ""
        year         = release_date[:4] if len(release_date) >= 4 else None

        vote_average = data.get("vote_average")
        rating       = f"{vote_average:.1f}" if vote_average else None

        genres = [g.get("name") for g in data.get("genres", []) if g.get("name")]
        tags   = ", ".join(genres)

        credits = data.get("credits", {})
        actors  = [cast.get("name") for cast in credits.get("cast", []) if cast.get("name")][:15]

        duration = data.get("runtime")
        if duration is None and item_type == "tv":
            runtimes = data.get("episode_run_time") or []
            duration = runtimes[0] if runtimes else None

        if item_type == "movie":
            return MovieInfo(
                url         = url,
                poster      = poster,
                title       = title,
                description = description,
                year        = year,
                rating      = rating,
                tags        = tags,
                actors      = actors,
                duration    = duration
            )
        else:
            seasons  = data.get("seasons", [])
            episodes = await self._get_tv_episodes(tmdb_id, seasons)
            return SeriesInfo(
                url         = url,
                poster      = poster,
                title       = title,
                description = description,
                year        = year,
                rating      = rating,
                tags        = tags,
                actors      = actors,
                duration    = duration,
                episodes    = episodes
            )

    async def _get_tv_episodes(self, tmdb_id: str, seasons: list) -> list[Episode]:
        async def _fetch_season_episodes(season_number: int) -> list[Episode]:
            try:
                resp = await self.httpx.get(
                    f"{self.tmdb_api}/tv/{tmdb_id}/season/{season_number}",
                    params  = {"api_key": self.tmdb_key},
                    headers = {"Referer": f"{self.main_url}/"}
                )
                if resp.status_code != 200:
                    return []

                season_data = resp.json()
                eps         = []
                for ep in season_data.get("episodes", []):
                    ep_num = ep.get("episode_number")
                    if ep_num:
                        eps.append(Episode(
                            season  = season_number,
                            episode = ep_num,
                            title   = ep.get("name") or f"Episode {ep_num}",
                            url     = f"https://solarmoviesz.com/player.html?id={tmdb_id}&type=tv&season={season_number}&episode={ep_num}"
                        ))
                return eps
            except Exception:
                return []

        tasks = []
        for season in seasons:
            season_number = season.get("season_number")
            if season_number is not None:
                tasks.append(_fetch_season_episodes(season_number))

        all_season_eps = await self.gather_with_limit(tasks)

        flat_episodes = []
        for eps in all_season_eps:
            flat_episodes.extend(eps)

        return sorted(flat_episodes, key=lambda x: (x.season, x.episode))

    async def load_links(self, url: str) -> list[ExtractResult]:
        await self._ensure_config()

        parsed    = urllib.parse.urlparse(url)
        params    = urllib.parse.parse_qs(parsed.query)
        tmdb_id   = params.get("id", [""])[0]
        item_type = params.get("type", ["movie"])[0]
        season    = params.get("season", ["1"])[0]
        episode   = params.get("episode", ["1"])[0]

        if not tmdb_id:
            return []

        results = []
        tasks   = []

        async def _extract_or_fallback(u: str, name: str) -> ExtractResult | list[ExtractResult]:
            extracted = await self.extract(u)
            if extracted:
                return extracted
            return ExtractResult(url=u, name=name, referer=self.main_url)

        for name, patterns in self.server_patterns.items():
            if item_type == "movie":
                embed_url = f"{patterns['movie']}{tmdb_id}"
            else:
                embed_url = f"{patterns['tv']}{tmdb_id}/{season}/{episode}"

            if name in ["VidCore", "VidFast"]:
                embed_url += "?autoPlay=true"

            tasks.append(_extract_or_fallback(embed_url, name))

        for res in await self.gather_with_limit(tasks):
            self.collect_results(results, res)

        return results
