# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import kekik_cache, PluginBase, MainPageResult, SearchResult, MovieInfo, Episode, SeriesInfo, ExtractResult, Subtitle
from httpx            import AsyncClient
from json             import dumps, loads
import re

class RecTV(PluginBase):
    name        = "RecTV"
    language    = "tr"
    main_url    = "https://a.prectv37.sbs"
    favicon     = "https://rectvapk.cc/wp-content/uploads/2023/02/Rec-TV.webp"
    description = "RecTv APK, Türkiye’deki en popüler Çevrimiçi Medya Akış platformlarından biridir. Filmlerin, Canlı Sporların, Web Dizilerinin ve çok daha fazlasının keyfini ücretsiz çıkarın."

    sw_key  = "4F5A9C3D9A86FA54EACEDDD635185/c3c5bd17-e37b-4b94-a944-8a3688a30452"
    http2   = AsyncClient(http2=True)
    http2.headers.update({"user-agent": "okhttp/4.12.0"})

    main_page   = {
        f"{main_url}/api/channel/by/filtres/0/0/SAYFA/{sw_key}/"      : "Canlı",
        f"{main_url}/api/movie/by/filtres/0/created/SAYFA/{sw_key}/"  : "Son Filmler",
        f"{main_url}/api/serie/by/filtres/0/created/SAYFA/{sw_key}/"  : "Son Diziler",
        f"{main_url}/api/movie/by/filtres/14/created/SAYFA/{sw_key}/" : "Aile",
        f"{main_url}/api/movie/by/filtres/1/created/SAYFA/{sw_key}/"  : "Aksiyon",
        f"{main_url}/api/movie/by/filtres/13/created/SAYFA/{sw_key}/" : "Animasyon",
        f"{main_url}/api/movie/by/filtres/19/created/SAYFA/{sw_key}/" : "Belgesel",
        f"{main_url}/api/movie/by/filtres/4/created/SAYFA/{sw_key}/"  : "Bilim Kurgu",
        f"{main_url}/api/movie/by/filtres/2/created/SAYFA/{sw_key}/"  : "Dram",
        f"{main_url}/api/movie/by/filtres/10/created/SAYFA/{sw_key}/" : "Fantastik",
        f"{main_url}/api/movie/by/filtres/3/created/SAYFA/{sw_key}/"  : "Komedi",
        f"{main_url}/api/movie/by/filtres/8/created/SAYFA/{sw_key}/"  : "Korku",
        f"{main_url}/api/movie/by/filtres/17/created/SAYFA/{sw_key}/" : "Macera",
        f"{main_url}/api/movie/by/filtres/5/created/SAYFA/{sw_key}/"  : "Romantik"
    }

    _data = {}

    @kekik_cache(ttl=60*60)
    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek   = await self.httpx.get(f"{url.replace('SAYFA', str(int(page) - 1))}")
        veriler = istek.json()

        return [
            MainPageResult(
                category = category,
                title    = self.clean_title(veri.get("title")),
                url      = dumps(veri),
                poster   = self.fix_url(veri.get("image")),
            )
                for veri in veriler
        ]

    @kekik_cache(ttl=60*60)
    async def search(self, query: str) -> list[SearchResult]:
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

    @kekik_cache(ttl=60*60)
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
                            "headers"   : self.media_handler.headers,
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

    @kekik_cache(ttl=15*60)
    async def load_links(self, url: str) -> list[str]:
        self.media_handler.headers.update({"User-Agent": "googleusercontent"})

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
                    "headers"   : self.media_handler.headers,
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