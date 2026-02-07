# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
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

    def get_payload(self, extra: dict) -> dict:
        base = {
            "_method": "GET",
            "_ApplicationId": self.app_id,
            "_JavaScriptKey": self.js_key,
            "_ClientVersion": "js3.4.1",
            "_InstallationId": "60f6b1a7-8860-4edf-b255-6bc465b6c704"
        }
        base.update(extra)
        return base

    main_page = {
        "movie" : "Movies",
        "tv"    : "TV Shows"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        api_url = self.movie_api if url == "movie" else self.tv_api
        skip    = (page - 1) * 20

        payload = self.get_payload({
            "limit": 20,
            "skip": skip,
            "order": "-updatedAt"
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
            href = f"{self.main_url}/detail/{item_type}/{item.get('objectId')}"

            if title:
                results.append(MainPageResult(
                    category = category,
                    title    = self.clean_title(title),
                    url      = href,
                    poster   = self.fix_url(poster)
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        results = []
        for api_url, item_type in [(self.movie_api, "movie"), (self.tv_api, "tv")]:
            payload = self.get_payload({
                "where": {"name": {"$regex": query, "$options": "i"}},
                "limit": 10
            })
            istek = await self.httpx.post(api_url, json=payload)
            data  = istek.json().get("results", [])

            for item in data:
                results.append(SearchResult(
                    title  = self.clean_title(item.get("name")),
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

        if item_type == "movie":
            return MovieInfo(
                url         = url,
                poster      = poster,
                title       = title,
                description = description,
                year        = str(year) if year else None,
                rating      = str(rating) if rating else None
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
                rating      = str(rating) if rating else None,
                episodes    = episodes
            )

    async def get_seasons_with_episodes(self, series_id: str) -> list[Episode]:
        # Sezonları al
        season_url = "https://parse.showflix.sbs/parse/classes/seasonv2"
        payload = self.get_payload({"where": {"seriesId": series_id}})
        istek = await self.httpx.post(season_url, json=payload)
        seasons = istek.json().get("results", [])

        all_episodes = []
        for season in seasons:
            season_id = season.get("objectId")
            season_num = int("".join(filter(str.isdigit, season.get("name", "1"))) or "1")

            # Bölümleri al
            episode_url = "https://parse.showflix.sbs/parse/classes/episodev2"
            ep_payload = self.get_payload({"where": {"seasonId": season_id}})
            ep_istek = await self.httpx.post(episode_url, json=ep_payload)
            eps = ep_istek.json().get("results", [])

            for ep in eps:
                # Gömülü linkleri 'data' alanında saklayabiliriz
                embeds = ep.get("embedLinks", {})
                data = {
                    "streamwish": embeds.get("streamwish"),
                    "streamruby": embeds.get("streamruby"),
                    "upnshare": embeds.get("upnshare"),
                    "vihide": embeds.get("vihide"),
                    "original": ep.get("originalURL")
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
            data = json.loads(url.replace("showflix://", ""))
            results = []

            mapping = {
                "streamwish": "https://embedwish.com/e/{}",
                "streamruby": "https://rubyvidhub.com/embed-{}.html",
                "upnshare": "https://showflix.upns.one/#{}",
                "vihide": "https://smoothpre.com/v/{}.html"
            }

            for key, template in mapping.items():
                if val := data.get(key):
                    res = await self.extract(template.format(val))
                    if res:
                        if isinstance(res, list):
                            results.extend(res)
                        else:
                            results.append(res)

            if val := data.get("original"):
                 results.append(ExtractResult(name="ShowFlix (Original)", url=val, referer=self.main_url))

            # Alt yazıları senkronize et
            all_subs = {}
            for res in results:
                for sub in res.subtitles:
                    if sub.name not in all_subs:
                        all_subs[sub.name] = sub

            unique_subs = list(all_subs.values())
            for res in results:
                res.subtitles = unique_subs

            return results

        # Movie Fallback
        parts     = url.split("/")
        obj_id    = parts[-1]
        payload   = self.get_payload({})
        istek     = await self.httpx.post(f"{self.movie_api}/{obj_id}", json=payload)
        item      = istek.json()
        embeds    = item.get("embedLinks", {})

        results = []
        mapping = {
            "streamwish": "https://embedwish.com/e/{}",
            "streamruby": "https://rubyvidhub.com/embed-{}.html",
            "upnshare": "https://showflix.upns.one/#{}",
            "vihide": "https://smoothpre.com/v/{}.html"
        }

        for key, template in mapping.items():
            if val := embeds.get(key):
                res = await self.extract(template.format(val))
                if res:
                    if isinstance(res, list):
                        results.extend(res)
                    else:
                        results.append(res)

        if val := item.get("originalURL"):
             results.append(ExtractResult(name="ShowFlix (Original)", url=val, referer=self.main_url))

        # Alt yazıları senkronize et
        all_subs = {}
        for res in results:
            for sub in res.subtitles:
                if sub.name not in all_subs:
                    all_subs[sub.name] = sub

        unique_subs = list(all_subs.values())
        for res in results:
            res.subtitles = unique_subs

        return results
