# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.CLI  import konsol
from KekikStream.Core import PluginBase, SearchResult, MovieInfo, Episode, SeriesInfo, ExtractResult, Subtitle
from httpx            import AsyncClient
from json             import dumps, loads
import re


class RecTV(PluginBase):
    name     = "RecTV"
    main_url = "https://c.prectv34.sbs"

    sw_key  = "4F5A9C3D9A86FA54EACEDDD635185/c3c5bd17-e37b-4b94-a944-8a3688a30452"
    http2   = AsyncClient(http2=True)
    http2.headers.update({"user-agent": "okhttp/4.12.0"})

    async def search(self, query: str) -> list[SearchResult]:
        self.media_handler.headers.update({"User-Agent": "googleusercontent"})

        istek     = await self.http2.get(f"{self.main_url}/api/search/{query}/{self.sw_key}/")

        kanallar  = istek.json().get("channels")
        icerikler = istek.json().get("posters")
        tum_veri  = {item['title']: item for item in kanallar + icerikler}.values()
        tum_veri  = sorted(tum_veri, key=lambda sozluk: sozluk["title"])

        tur_ver   = lambda veri: " | Dizi" if veri.get("type") == "serie" else " | Film"

        return [
            SearchResult(
                title  = veri.get("title") + tur_ver(veri),
                url    = dumps(veri),
                poster = self.fix_url(veri.get("image")),
            )
                for veri in tum_veri
        ]

    async def load_item(self, url: str) -> MovieInfo:
        veri = loads(url)

        match veri.get("type"):
            case "serie":
                dizi_istek = await self.http2.get(f"{self.main_url}/api/season/by/serie/{veri.get('id')}/{self.sw_key}/")
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
                            "ext_name"  : self.name,
                            "name"      : f"{veri.get('title')} | {ep_model.season}. Sezon {ep_model.episode}. Bölüm",
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
                    "ext_name"  : self.name,
                    "name"      : veri.get("title"),
                    "referer"   : "https://twitter.com/",
                    "subtitles" : []
                }
                videolar.append(video_link)

        return videolar

    async def play(self, name: str, url: str, referer: str, subtitles: list[Subtitle]):
        extract_result = ExtractResult(name=name, url=url, referer=referer, subtitles=subtitles)
        self.media_handler.title = name
        if self.name not in self.media_handler.title:
            self.media_handler.title = f"{self.name} | {self.media_handler.title}"

        self.media_handler.play_media(extract_result)