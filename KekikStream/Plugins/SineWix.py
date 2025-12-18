# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, Episode, SeriesInfo, ExtractResult, Subtitle
import json

class SineWix(PluginBase):
    name        = "SineWix"
    language    = "tr"
    main_url    = "http://10.0.0.2:2585"
    favicon     = "https://play-lh.googleusercontent.com/brwGNmr7IjA_MKk_TTPs0va10hdKE_bD_a1lnKoiMuCayW98EHpRv55edA6aEoJlmwfX"
    description = "Sinewix | Ücretsiz Film - Dizi - Anime İzleme Uygulaması"

    main_page   = {
        f"{main_url}/sinewix/movies"        : "Filmler",
        f"{main_url}/sinewix/series"        : "Diziler",
        f"{main_url}/sinewix/animes"        : "Animeler",
        f"{main_url}/sinewix/movies/10751"  : "Aile",
        f"{main_url}/sinewix/movies/28"     : "Aksiyon",
        f"{main_url}/sinewix/movies/16"     : "Animasyon",
        f"{main_url}/sinewix/movies/99"     : "Belgesel",
        f"{main_url}/sinewix/movies/10765"  : "Bilim Kurgu & Fantazi",
        f"{main_url}/sinewix/movies/878"    : "Bilim-Kurgu",
        f"{main_url}/sinewix/movies/18"     : "Dram",
        f"{main_url}/sinewix/movies/14"     : "Fantastik",
        f"{main_url}/sinewix/movies/53"     : "Gerilim",
        f"{main_url}/sinewix/movies/9648"   : "Gizem",
        f"{main_url}/sinewix/movies/35"     : "Komedi",
        f"{main_url}/sinewix/movies/27"     : "Korku",
        f"{main_url}/sinewix/movies/12"     : "Macera",
        f"{main_url}/sinewix/movies/10402"  : "Müzik",
        f"{main_url}/sinewix/movies/10749"  : "Romantik",
        f"{main_url}/sinewix/movies/10752"  : "Savaş",
        f"{main_url}/sinewix/movies/80"     : "Suç",
        f"{main_url}/sinewix/movies/10770"  : "TV film",
        f"{main_url}/sinewix/movies/36"     : "Tarih",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek   = await self.httpx.get(f"{url}/{page}")
        veriler = istek.json()

        return [
            MainPageResult(
                category = category,
                title    = veri.get("title") or veri.get("name"),
                url      = f"?type={veri.get('type')}&id={veri.get('id')}",
                poster   = self.fix_url(veri.get("poster_path")),
            )
                for veri in veriler.get("data")
        ]

    async def search(self, query: str) -> list[SearchResult]:
        istek = await self.httpx.get(f"{self.main_url}/sinewix/search/{query}")

        return [
            SearchResult(
                title  = veri.get("name"),
                url    = f"?type={veri.get('type')}&id={veri.get('id')}",
                poster = self.fix_url(veri.get("poster_path")),
            )
                for veri in istek.json().get("search")
        ]

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        item_type = url.split("?type=")[-1].split("&id=")[0]
        item_id   = url.split("&id=")[-1]

        istek = await self.httpx.get(f"{self.main_url}/sinewix/{item_type}/{item_id}")
        veri  = istek.json()

        match item_type:
            case "movie":
                org_title = veri.get("title")
                alt_title = veri.get("original_name") or ""
                title     = f"{org_title} - {alt_title}" if (alt_title and org_title != alt_title)  else org_title

                return MovieInfo(
                    url         = self.fix_url(f"{self.main_url}/sinewix/{item_type}/{item_id}"),
                    poster      = self.fix_url(veri.get("poster_path")),
                    title       = title,
                    description = veri.get("overview"),
                    tags        = [genre.get("name") for genre in veri.get("genres")],
                    rating      = veri.get("vote_average"),
                    year        = veri.get("release_date"),
                    actors      = [actor.get("name") for actor in veri.get("casterslist")],
                )
            case _:
                org_title = veri.get("name")
                alt_title = veri.get("original_name") or ""
                title     = f"{org_title} - {alt_title}" if (alt_title and org_title != alt_title)  else org_title

                episodes = []
                for season in veri.get("seasons"):
                    for episode in season.get("episodes"):
                        if not episode.get("videos"):
                            continue

                        # Bölüm için gerekli bilgileri JSON olarak sakla
                        ep_data = {
                            "url"        : self.fix_url(episode.get("videos")[0].get("link")),
                            "title"      : self.name,
                            "is_episode" : True
                        }

                        ep_model = Episode(
                            season  = season.get("season_number"),
                            episode = episode.get("episode_number"),
                            title   = episode.get("name"),
                            url     = json.dumps(ep_data),
                        )

                        episodes.append(ep_model)

                return SeriesInfo(
                    url         = self.fix_url(f"{self.main_url}/sinewix/{item_type}/{item_id}"),
                    poster      = self.fix_url(veri.get("poster_path")),
                    title       = title,
                    description = veri.get("overview"),
                    tags        = [genre.get("name") for genre in veri.get("genres")],
                    rating      = veri.get("vote_average"),
                    year        = veri.get("first_air_date"),
                    actors      = [actor.get("name") for actor in veri.get("casterslist")],
                    episodes    = episodes,
                )

    async def load_links(self, url: str) -> list[dict]:
        try:
            veri = json.loads(url)
            if veri.get("is_episode"):
                return [{
                    "url"     : veri.get("url"),
                    "name"    : veri.get("title"),
                    "referer" : self.main_url
                }]
        except Exception:
            pass

        # Eğer JSON değilse ve direkt URL ise (eski yapı veya harici link)
        if not url.startswith(self.main_url) and not url.startswith("{"):
             return [{"url": url, "name": "Video"}]

        istek = await self.httpx.get(url)
        veri  = istek.json()

        org_title = veri.get("title")
        alt_title = veri.get("original_name") or ""
        title     = f"{org_title} - {alt_title}" if (alt_title and org_title != alt_title)  else org_title

        results = []
        for video in veri.get("videos"):
            video_link = video.get("link").split("_blank\">")[-1]
            results.append({
                "url"     : video_link,
                "name"    : f"{self.name}",
                "referer" : self.main_url
            })

        return results

    async def play(self, **kwargs):
        extract_result = ExtractResult(**kwargs)
        self.media_handler.title = kwargs.get("name")
        if self.name not in self.media_handler.title:
            self.media_handler.title = f"{self.name} | {self.media_handler.title}"

        self.media_handler.play_media(extract_result)
