# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult
import datetime
import json
import urllib.parse


class DramaFlix(PluginBase):
    name        = "DramaFlix"
    language    = "tr"
    main_url    = "https://dramaflix.cc"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "DramaFlix - Asya dramaları ve kısa diziler için dijital platform. Popüler platformlardan en yeni içerikler."

    _api_url = f"{main_url}/api/series"

    main_page = {
        "DramaWave" : "DramaWave",
        "ShortMax"  : "ShortMax",
        "DramaBite" : "DramaBite",
        "NetShort"  : "NetShort",
        "DramaBox"  : "DramaBox",
        "FlexTV"    : "FlexTV",
        "ReelShort" : "ReelShort",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        limit  = 25
        offset = (page - 1) * limit
        api    = f"{self._api_url}?limit={limit}&offset={offset}&language=TR&platform={url}"

        istek = await self.httpx.get(api)
        data  = istek.json()

        results = []
        for item in data:
            title = item.get("title")
            slug  = item.get("slug")

            if title and slug:
                safe_slug = urllib.parse.quote(slug)
                results.append(
                    MainPageResult(
                        category = category,
                        title    = title,
                        url      = f"{self._api_url}/{safe_slug}",
                        poster   = self.fix_url(item.get("cover_image")),
                    )
                )

        return results

    async def search(self, query: str) -> list[SearchResult]:
        api   = f"{self._api_url}?search={query}&language=TR&limit=500"
        istek = await self.httpx.get(api)
        data  = istek.json()

        results = []
        for item in data:
            title = item.get("title")
            slug  = item.get("slug")

            if title and slug:
                safe_slug = urllib.parse.quote(slug)
                results.append(SearchResult(title=title, url=f"{self._api_url}/{safe_slug}", poster=self.fix_url(item.get("cover_image"))))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek = await self.httpx.get(url)
        data  = istek.json()

        series = data.get("series", {})
        title  = series.get("title", "Bilinmeyen")
        desc   = series.get("description") or series.get("used_description") or f"{title} dizisini DramaFlix farkıyla izleyin."

        tags = [series.get("platform")] if series.get("platform") else []
        # Actors meta alanını API credits'ten doldur
        actors = [c.get("name") for c in series.get("credits", []) if c.get("name")]

        created_at = series.get("createdAt")
        year       = None
        if created_at:
            year = str(datetime.datetime.fromtimestamp(created_at / 1000.0).year)

        episodes = []
        for ep in data.get("episodes", []):
            ep_num      = ep.get("episode_number")
            ep_url_data = {"url": ep.get("url"), "subtitles": ep.get("subtitles", [])}

            episodes.append(Episode(season=1, episode=ep_num, title=f"Bölüm {ep_num}", url=json.dumps(ep_url_data)))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(series.get("cover_image")),
            title       = title,
            description = desc,
            tags        = tags,
            year        = year,
            actors      = actors,
            episodes    = episodes,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        try:
            data      = json.loads(url)
            video_url = data.get("url")
            if not video_url:
                return []

            subtitles = []
            for sub in data.get("subtitles", []):
                lang = sub.get("label") or sub.get("language") or "Bilinmeyen"
                subtitles.append(self.new_subtitle(self.fix_url(sub.get("url")), lang))

            return [ExtractResult(name=self.name, url=self.fix_url(video_url), referer=f"{self.main_url}/", subtitles=subtitles)]
        except:
            return []
