# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult
import json

class ShowFlix(PluginBase):
    name        = "ShowFlix"
    language    = "en"
    main_url    = "https://showflix.store"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Showflix - Watch and Download Latest Movies and TV Shows for Free. Stream in HD with No Ads!"

    # Kotlin'den gelen API endpoint'leri
    movie_api = "https://parse.showflix.sbs/parse/classes/moviesv2"
    tv_api    = "https://parse.showflix.sbs/parse/classes/seriesv2"

    # Parse API ayarları (Kotlin'den uyarlandı) - Bu placeholder'lar çalışıyor!
    app_id   = "SHOWFLIXAPPID"
    js_key   = "SHOWFLIXMASTERKEY"
    tmdb_api = "https://api.themoviedb.org/3"
    tmdb_key = "1865f43a0549ca50d341dd9ab8b29f49"

    def get_payload(self, extra: dict) -> dict:
        base = {
            "_method"         : "GET",
            "_ApplicationId"  : self.app_id,
            "_JavaScriptKey"  : self.js_key,
            "_ClientVersion"  : "js3.4.1",
            "_InstallationId" : "60f6b1a7-8860-4edf-b255-6bc465b6c704"
        }
        base.update(extra)
        return base

    async def _get_tmdb_metadata(self, tmdb_id: int | str | None, item_type: str) -> dict:
        if not tmdb_id:
            return {}

        media_type = "movie" if item_type == "movie" else "tv"
        try:
            resp = await self.httpx.get(
                f"{self.tmdb_api}/{media_type}/{tmdb_id}",
                params = {
                    "api_key"            : self.tmdb_key,
                    "append_to_response" : "credits"
                },
                headers = {"Referer": f"{self.main_url}/"}
            )
            return resp.json() if resp.status_code == 200 else {}
        except Exception:
            return {}

    main_page = {
        "movie" : "Movies",
        "tv"    : "TV Shows"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        api_url = self.movie_api if url == "movie" else self.tv_api
        skip    = (page - 1) * 20

        payload = self.get_payload({
            "limit" : 20,
            "skip"  : skip,
            "order" : "-updatedAt"
        })

        istek = await self.httpx.post(api_url, json=payload)
        data  = istek.json().get("results", [])

        results = []
        for item in data:
            title  = item.get("name")
            poster = item.get("posterURL") or item.get("image")
            # Detay sayfasına gitmek için ID'yi kullanacağız, ancak Plugin yapısına uygun bir URL uydurmalıyız
            # load_item içinde bu URL'den ID'yi geri alacağız
            item_type = "movie" if url == "movie" else "tv"
            href      = f"{self.main_url}/detail/{item_type}/{item.get('objectId')}"

            if title:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = href,
                    poster   = self.fix_url(poster)
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        results = []
        headers = {
            "X-Parse-Application-Id" : self.app_id,
            "X-Parse-JavaScript-Key" : self.js_key
        }

        # Determine search criteria
        if query.isdigit() and 3 < len(query) < 8:
            # Query looks like a TMDB ID
            where = {"tmdbId": int(query)}
        else:
            where = {"name": {"$regex": query, "$options": "i"}}

        params = {
            "where" : json.dumps(where),
            "limit" : 25,
            "order" : "-updatedAt"
        }

        async def _safe_search(api_url):
            try:
                return await self.httpx.get(api_url, params=params, headers=headers)
            except Exception as e:
                return e

        api_mapping = [(self.movie_api, "movie"), (self.tv_api, "tv")]
        tasks       = [_safe_search(api_url) for api_url, _ in api_mapping]
        responses   = await self.gather_with_limit(tasks)

        for i, resp in enumerate(responses):
            if isinstance(resp, Exception) or resp.status_code != 200:
                continue

            item_type = api_mapping[i][1]
            data      = resp.json().get("results", [])
            for item in data:
                results.append(SearchResult(
                    title  = item.get("name"),
                    url    = f"{self.main_url}/detail/{item_type}/{item.get('objectId')}",
                    poster = self.fix_url(item.get("posterURL") or item.get("image"))
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        # URL formatımız: .../detail/{type}/{id}
        parts     = url.split("/")
        item_type = parts[-2]
        obj_id    = parts[-1]

        api_url = self.movie_api if item_type == "movie" else self.tv_api
        payload = self.get_payload({})

        istek = await self.httpx.post(f"{api_url}/{obj_id}", json=payload)
        item  = istek.json()

        title       = item.get("name")
        poster      = self.fix_url(item.get("posterURL") or item.get("image"))
        description = item.get("storyline") or item.get("description")
        year        = item.get("releaseYear") or item.get("year")
        rating      = item.get("rating")
        genres      = item.get("genres", [])
        tags        = ", ".join(genres) if isinstance(genres, list) else genres
        tmdb_meta   = await self._get_tmdb_metadata(item.get("tmdbId"), item_type)
        actors      = [cast.get("name") for cast in tmdb_meta.get("credits", {}).get("cast", []) if cast.get("name")][:10]
        duration    = tmdb_meta.get("runtime")

        if duration is None and item_type != "movie":
            runtimes = tmdb_meta.get("episode_run_time") or []
            duration = runtimes[0] if runtimes else None

        if item_type == "movie":
            return MovieInfo(
                url         = url,
                poster      = poster,
                title       = title,
                description = description,
                year        = str(year) if year else None,
                rating      = str(rating).strip() if rating else None,
                tags        = tags,
                actors      = actors,
                duration    = duration
            )
        else:
            # Sezon ve bölümleri ayrı API çağrılarıyla alıyoruz
            episodes = await self.get_seasons_with_episodes(obj_id)

            return SeriesInfo(
                url         = url,
                poster      = poster,
                title       = title,
                description = description,
                year        = str(year) if year else None,
                rating      = str(rating).strip() if rating else None,
                tags        = tags,
                actors      = actors,
                duration    = duration,
                episodes    = episodes
            )

    async def get_seasons_with_episodes(self, series_id: str) -> list[Episode]:
        # Sezonları al
        season_url = "https://parse.showflix.sbs/parse/classes/seasonv2"
        payload    = self.get_payload({"where": json.dumps({"seriesId": series_id})})
        istek      = await self.httpx.post(season_url, json=payload)
        seasons    = istek.json().get("results", [])

        all_episodes = []
        for season in seasons:
            season_id  = season.get("objectId")
            season_num = int("".join(filter(str.isdigit, season.get("name", "1"))) or "1")

            # Bölümleri al
            episode_url = "https://parse.showflix.sbs/parse/classes/episodev2"
            ep_payload  = self.get_payload({"where": json.dumps({"seasonId": season_id})})
            ep_istek    = await self.httpx.post(episode_url, json=ep_payload)
            eps         = ep_istek.json().get("results", [])

            for ep in eps:
                # Gömülü linkleri 'data' alanında saklayabiliriz
                embeds = ep.get("embedLinks", {})
                data   = {
                    "streamwish" : embeds.get("streamwish"),
                    "streamruby" : embeds.get("streamruby"),
                    "upnshare"   : embeds.get("upnshare"),
                    "vihide"     : embeds.get("vihide"),
                    "original"   : ep.get("originalURL")
                }

                all_episodes.append(Episode(
                    season  = season_num,
                    episode = ep.get("episodeNumber", 1),
                    title   = ep.get("name"),
                    url     = f"showflix://{json.dumps(data)}" # Custom protocol for load_links
                ))

        return sorted(all_episodes, key=lambda x: (x.season, x.episode))

    async def load_links(self, url: str) -> list[ExtractResult]:
        if url.startswith("showflix://"):
            data    = json.loads(url.replace("showflix://", ""))
            results = []

            mapping = {
                "streamwish" : "https://embedwish.com/e/{}",
                "streamruby" : "https://rubyvidhub.com/embed-{}.html",
                "upnshare"   : "https://showflix.upns.one/  #{}",
                "vihide"     : "https://smoothpre.com/v/{}.html"
            }

            tasks = [self.extract(template.format(val)) for key, template in mapping.items() if (val := data.get(key))]
            for res in await self.gather_with_limit(tasks):
                self.collect_results(results, res)

            if val := data.get("original"):
                 results.append(ExtractResult(name="Original", url=val, referer=self.main_url))

            return results

        # Movie Fallback
        parts   = url.split("/")
        obj_id  = parts[-1]
        payload = self.get_payload({})
        istek   = await self.httpx.post(f"{self.movie_api}/{obj_id}", json=payload)
        item    = istek.json()
        embeds  = item.get("embedLinks", {})

        results = []
        mapping = {
            "streamwish" : "https://embedwish.com/e/{}",
            "streamruby" : "https://rubyvidhub.com/embed-{}.html",
            "upnshare"   : "https://showflix.upns.one/  #{}",
            "vihide"     : "https://smoothpre.com/v/{}.html"
        }

        tasks = [self.extract(template.format(val)) for key, template in mapping.items() if (val := embeds.get(key))]
        for res in await self.gather_with_limit(tasks):
            self.collect_results(results, res)

        if val := item.get("originalURL"):
             results.append(ExtractResult(name="Original", url=val, referer=self.main_url))

        return results
