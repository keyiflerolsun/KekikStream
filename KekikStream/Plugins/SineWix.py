# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, Episode, SeriesInfo, ExtractResult
import re

class SineWix(PluginBase):
    name        = "SineWix"
    language    = "tr"
    main_url    = "http://px-webservisler:2585"
    favicon     = "https://play-lh.googleusercontent.com/brwGNmr7IjA_MKk_TTPs0va10hdKE_bD_a1lnKoiMuCayW98EHpRv55edA6aEoJlmwfX"
    description = "Sinewix | Ücretsiz Film - Dizi - Anime İzleme Uygulaması"

    main_page   = {
        f"{main_url}/sinewix/movies"       : "Filmler",
        f"{main_url}/sinewix/series"       : "Diziler",
        f"{main_url}/sinewix/animes"       : "Animeler",
        f"{main_url}/sinewix/movies/10751" : "Aile",
        f"{main_url}/sinewix/movies/28"    : "Aksiyon",
        f"{main_url}/sinewix/movies/16"    : "Animasyon",
        f"{main_url}/sinewix/movies/99"    : "Belgesel",
        f"{main_url}/sinewix/movies/10765" : "Bilim Kurgu & Fantazi",
        f"{main_url}/sinewix/movies/878"   : "Bilim-Kurgu",
        f"{main_url}/sinewix/movies/18"    : "Dram",
        f"{main_url}/sinewix/movies/14"    : "Fantastik",
        f"{main_url}/sinewix/movies/53"    : "Gerilim",
        f"{main_url}/sinewix/movies/9648"  : "Gizem",
        f"{main_url}/sinewix/movies/35"    : "Komedi",
        f"{main_url}/sinewix/movies/27"    : "Korku",
        f"{main_url}/sinewix/movies/12"    : "Macera",
        f"{main_url}/sinewix/movies/10402" : "Müzik",
        f"{main_url}/sinewix/movies/10749" : "Romantik",
        f"{main_url}/sinewix/movies/10752" : "Savaş",
        f"{main_url}/sinewix/movies/80"    : "Suç",
        f"{main_url}/sinewix/movies/10770" : "TV film",
        f"{main_url}/sinewix/movies/36"    : "Tarih",
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
                for veri in veriler.get("data", [])
        ]

    async def search(self, query: str) -> list[SearchResult]:
        istek = await self.httpx.get(f"{self.main_url}/sinewix/search/{query}")

        return [
            SearchResult(
                title  = veri.get("name"),
                url    = f"?type={veri.get('type')}&id={veri.get('id')}",
                poster = self.fix_url(veri.get("poster_path")),
            )
                for veri in istek.json().get("search", [])
        ]

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        item_type = url.split("?type=")[-1].split("&id=")[0]
        item_id   = url.split("&id=")[-1]

        veri = (await self.httpx.get(f"{self.main_url}/sinewix/{item_type}/{item_id}")).json()

        common_data = {
            "url"         : self.fix_url(f"{self.main_url}/sinewix/{item_type}/{item_id}"),
            "poster"      : self.fix_url(veri.get("poster_path")),
            "title"       : f"{veri.get('title') or veri.get('name')} - {veri.get('original_name', '')}".strip(" - "),
            "description" : veri.get("overview"),
            "tags"        : [genre.get("name") for genre in veri.get("genres", [])],
            "rating"      : veri.get("vote_average"),
            "actors"      : [actor.get("name") for actor in veri.get("casterslist", [])],
        }

        if item_type == "movie":
            return MovieInfo(**common_data, year=veri.get("release_date", "")[:4] or None)

        episodes = []
        for season in veri.get("seasons", []):
            for episode in season.get("episodes", []):
                if not episode.get("videos"):
                    continue

                episodes.append(Episode(
                    season  = season.get("season_number"),
                    episode = episode.get("episode_number"),
                    title   = episode.get("name"),
                    url     = f"{self.main_url}/sinewix/{item_type}/{item_id}/season/{season.get('season_number')}/episode/{episode.get('episode_number')}"
                ))

        return SeriesInfo(**common_data, year=veri.get("first_air_date", "")[:4] or None, episodes=episodes)

    async def load_links(self, url: str) -> list[ExtractResult]:
        # 1. Eğer halihazırda bir video linkiyse (API değilse) direkt dön
        ua = self.httpx.headers.get("User-Agent")
        if not url.startswith(self.main_url) and not url.startswith("?"):
            return [ExtractResult(url=url, name=self.name, user_agent=ua)]

        # 2. Kısa URL'yi API URL'sine çevir
        if url.startswith("?"):
            item_type = url.split("type=")[-1].split("&id=")[0]
            item_id   = url.split("&id=")[-1]
            url       = f"{self.main_url}/sinewix/{item_type}/{item_id}"

        # 3. API'den veriyi çek ve mirrorları işle
        veri    = (await self.httpx.get(url)).json()
        sources = veri.get("videos") or [{"link": veri.get("link")}]

        results = []
        for source in sources:
            if not (raw_link := source.get("link")):
                continue

            clean_link = re.sub(r'<[^>]*>', '', raw_link.split('_blank">')[-1])
            final_url  = self.fix_url(clean_link)

            # Akıllı Referer: Linkin kendi domainini referer yapıyoruz
            try:
                domain_referer = f"{final_url.split('://')[0]}://{final_url.split('/')[2]}/"
            except:
                domain_referer = None

            results.append(ExtractResult(
                url        = final_url,
                name       = self.name,
                referer    = domain_referer,
                user_agent = ua
            ))

        return results
