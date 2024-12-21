# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.CLI                  import konsol
from KekikStream.Core                 import PluginBase, SearchResult, MovieInfo, Episode, SeriesInfo
from KekikStream.Core.ExtractorModels import ExtractResult, Subtitle
from httpx                            import AsyncClient
from json                             import dumps, loads
import re


class RecTV(PluginBase):
    name     = "RecTV"
    main_url = "https://m.prectv7.sbs"

    sw_key   = "4F5A9C3D9A86FA54EACEDDD635185/c3c5bd17-e37b-4b94-a944-8a3688a30452"
    oturum   = AsyncClient(http2=True)
    oturum.headers.update({"user-agent": "okhttp/4.12.0"})

    async def search(self, query: str) -> list[SearchResult]:
        istek     = await self.oturum.get(f"{self.main_url}/api/search/{query}/{self.sw_key}/")

        kanallar  = istek.json().get("channels")
        kanallar  = sorted(kanallar, key=lambda sozluk: sozluk["title"])

        icerikler = istek.json().get("posters")
        icerikler = sorted(icerikler, key=lambda sozluk: sozluk["title"])

        return [
            SearchResult(
                title  = veri.get("title"),
                url    = dumps(veri),
                poster = self.fix_url(veri.get("image")),
            )
                for veri in [*kanallar, *icerikler]
        ]

    async def load_item(self, url: str) -> MovieInfo:
        veri = loads(url)

        match veri.get("type"):
            case "serie":
                dizi_istek = await self.oturum.get(f"{self.main_url}/api/season/by/serie/{veri.get('id')}/{self.sw_key}/")
                dizi_veri  = dizi_istek.json()

                episodes = []
                for season in dizi_veri:
                    for episode in season.get("episodes"):
                        ep_model = Episode(
                            season  = int(re.search(r"(\d+)\.S", season.get("title")).group(1)) if re.search(r"(\d+)\.S", season.get("title")) else 1,
                            episode = int(re.search(r"Bölüm (\d+)", episode.get("title")).group(1)) if re.search(r"Bölüm (\d+)", episode.get("title")) else 1,
                            title   = episode.get("title"),
                            url     = self.fix_url(episode.get("sources")[0].get("url")),
                        )

                        episodes.append(ep_model)

                        self._data[ep_model.url] = {
                            "name"      : f"{veri.get('title')} | {ep_model.season}. Sezon {ep_model.episode}. Bölüm - {ep_model.title}",
                            "referer"   : "https://twitter.com/",
                            "subtitles" : []
                        }

                return SeriesInfo(
                    url         = url,
                    poster      = self.fix_url(veri.get("image")),
                    title       = veri.get("title"),
                    description = veri.get("description"),
                    tags        = [genre.get("title") for genre in veri.get("genres")] if veri.get("genres") else [],
                    rating      = veri.get("imdb") or veri.get("rating"),
                    year        = veri.get("year"),
                    actors      = [],
                    episodes    = episodes
                )
            case _:
                return MovieInfo(
                    url         = url,
                    poster      = self.fix_url(veri.get("image")),
                    title       = veri.get("title"),
                    description = veri.get("description"),
                    tags        = [genre.get("title") for genre in veri.get("genres")] if veri.get("genres") else [],
                    rating      = veri.get("imdb") or veri.get("rating"),
                    year        = veri.get("year"),
                    actors      = []
                )

    async def load_links(self, url: str) -> list[str]:
        try:
            veri = loads(url)
        except Exception:
            return [url]

        videolar = []
        if veri.get("sources"):
            for kaynak in veri.get("sources"):
                video_link = kaynak.get("url")
                if "otolinkaff" in video_link:
                    continue

                self._data[video_link] = {
                    "name"      : veri.get("title"),
                    "referer"   : "https://twitter.com/",
                    "subtitles" : []
                }
                videolar.append(video_link)

            return videolar

    async def play(self, name: str, url: str, referer: str, subtitles: list[Subtitle]):
        extract_result = ExtractResult(name=name, url=url, referer=referer, subtitles=subtitles)
        self.media_handler.title = name
        self.media_handler.play_media(extract_result)