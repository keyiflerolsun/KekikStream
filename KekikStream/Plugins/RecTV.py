# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import kekik_cache, PluginBase, MainPageResult, SearchResult, MovieInfo, Episode, SeriesInfo, ExtractResult, Subtitle
from json             import dumps, loads
import re

class RecTV(PluginBase):
    name        = "RecTV"
    language    = "tr"
    main_url    = "https://m.prectv60.lol"
    favicon     = "https://rectvapk.cc/wp-content/uploads/2023/02/Rec-TV.webp"
    description = "RecTv APK, Türkiye’deki en popüler Çevrimiçi Medya Akış platformlarından biridir. Filmlerin, Canlı Sporların, Web Dizilerinin ve çok daha fazlasının keyfini ücretsiz çıkarın."

    sw_key = "4F5A9C3D9A86FA54EACEDDD635185/c3c5bd17-e37b-4b94-a944-8a3688a30452"

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

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        self.httpx.headers.update({"user-agent": "okhttp/4.12.0"})
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

    async def search(self, query: str) -> list[SearchResult]:
        self.httpx.headers.update({"user-agent": "okhttp/4.12.0"})
        istek     = await self.httpx.get(f"{self.main_url}/api/search/{query}/{self.sw_key}/")

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
        self.httpx.headers.update({"user-agent": "okhttp/4.12.0"})
        veri = loads(url)

        match veri.get("type"):
            case "serie":
                dizi_istek = await self.httpx.get(f"{self.main_url}/api/season/by/serie/{veri.get('id')}/{self.sw_key}/")
                dizi_veri  = dizi_istek.json()

                episodes = []
                for season in dizi_veri:
                    for episode in season.get("episodes"):
                        # Bölüm için gerekli bilgileri JSON olarak sakla
                        ep_data = {
                            "url"        : self.fix_url(episode.get("sources")[0].get("url")),
                            "title"      : f"{veri.get('title')} | {season.get('title', '1. Sezon')} {episode.get('title', '1. Bölüm')}",
                            "is_episode" : True
                        }
                        
                        ep_model = Episode(
                            season  = int(re.search(r"(\d+)\.S", season.get("title")).group(1)) if re.search(r"(\d+)\.S", season.get("title")) else 1,
                            episode = int(re.search(r"Bölüm (\d+)", episode.get("title")).group(1)) if re.search(r"Bölüm (\d+)", episode.get("title")) else 1,
                            title   = episode.get("title"),
                            url     = dumps(ep_data),
                        )

                        episodes.append(ep_model)

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

    #@kekik_cache(ttl=15*60)
    async def load_links(self, url: str) -> list[dict]:
        try:
            veri = loads(url)
        except Exception:
            # JSON değilse düz URL'dir (eski yapı veya hata)
            return [{"url": url, "name": "Video"}]

        # Eğer dizi bölümü ise (bizim oluşturduğumuz yapı)
        if veri.get("is_episode"):
            return [{
                "url"        : veri.get("url"),
                "name"       : veri.get("title", "Bölüm"),
                "user_agent" : "googleusercontent",
                "referer"    : "https://twitter.com/"
            }]

        # Film ise (RecTV API yapısı)
        results = []
        if veri.get("sources"):
            for kaynak in veri.get("sources"):
                video_link = kaynak.get("url")
                if "otolinkaff" in video_link:
                    continue

                results.append({
                    "url"        : video_link,
                    "name"       : f"{veri.get('title')} - {kaynak.get('title')}",
                    "user_agent" : "googleusercontent",
                    "referer"    : "https://twitter.com/"
                })

        return results

    async def play(self, **kwargs):
        extract_result = ExtractResult(**kwargs)
        self.media_handler.title = kwargs.get("name")
        if self.name not in self.media_handler.title:
            self.media_handler.title = f"{self.name} | {self.media_handler.title}"

        self.media_handler.play_media(extract_result)