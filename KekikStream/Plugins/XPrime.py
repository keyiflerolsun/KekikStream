# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult

class XPrime(PluginBase):
    name        = "XPrime"
    language    = "tr"
    main_url    = "https://api.themoviedb.org/3"
    favicon     = "https://xprime.stream/favicon/favicon-xmas.ico"
    description = "XPrime - Primenet, EEK ve diğer sunucular üzerinden yüksek kaliteli film izleme platformu."

    _api_key      = "84259f99204eeb7d45c7e3d8e36c6123"
    _img_url      = "https://image.tmdb.org/t/p/w500"
    _back_img_url = "https://image.tmdb.org/t/p/w780"
    _api_url      = "http://100.100.1.101:2585/api/v1/xprime"

    main_page = {
        f"{main_url}/trending/movie/week?api_key={_api_key}&language=tr-TR&page=SAYFA" : "Haftanın Popülerleri",
        f"{main_url}/movie/now_playing?api_key={_api_key}&language=tr-TR&page=SAYFA"   : "Vizyondakiler",
        f"{main_url}/movie/top_rated?api_key={_api_key}&language=tr-TR&page=SAYFA"     : "En Yüksek Puanlılar",
        "28"                                                                           : "Aksiyon",
        "12"                                                                           : "Macera",
        "16"                                                                           : "Animasyon",
        "35"                                                                           : "Komedi",
        "80"                                                                           : "Suç",
        "99"                                                                           : "Belgesel",
        "18"                                                                           : "Dram",
        "10751"                                                                        : "Aile",
        "14"                                                                           : "Fantastik",
        "36"                                                                           : "Tarih",
        "27"                                                                           : "Korku",
        "9648"                                                                         : "Gizem",
        "10402"                                                                        : "Müzik",
        "10749"                                                                        : "Romantik",
        "878"                                                                          : "Bilim Kurgu",
        "53"                                                                           : "Gerilim",
        "10752"                                                                        : "Savaş",
        "37"                                                                           : "Vahşi Batı",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        if "SAYFA" in url:
            target_url = url.replace("SAYFA", str(page))
        else:
            target_url = (
                f"{self.main_url}/discover/movie?api_key={self._api_key}&page={page}"
                f"&include_adult=false&with_watch_monetization_types=flatrate%7Cfree%7Cads"
                f"&watch_region=TR&language=tr-TR&with_genres={url}&sort_by=popularity.desc"
            )

        istek   = await self.httpx.get(target_url)
        veriler = istek.json().get("results", [])

        return [
            MainPageResult(
                category = category,
                title    = veri.get("title"),
                url      = str(veri.get("id")),
                poster   = self.fix_url(self._img_url + (veri.get("poster_path") or "")),
            )
                for veri in veriler
                if veri.get("title") and veri.get("id")
        ]

    async def search(self, query: str) -> list[SearchResult]:
        istek   = await self.httpx.get(f"{self.main_url}/search/multi?api_key={self._api_key}&query={query}&page=1")
        veriler = istek.json().get("results", [])

        return [
            SearchResult(
                title  = veri.get("title"),
                url    = str(veri.get("id")),
                poster = self.fix_url(self._img_url + (veri.get("poster_path") or "")),
            )
                for veri in veriler
                if veri.get("media_type") == "movie" and veri.get("title") and veri.get("id")
        ]

    async def load_item(self, url: str) -> MovieInfo:
        istek = await self.httpx.get(
            f"{self.main_url}/movie/{url}?api_key={self._api_key}&language=tr-TR&append_to_response=credits"
        )
        film = istek.json()

        title       = film.get("title")
        org_title   = film.get("original_title")
        final_title = f"{org_title} - {title}" if title and org_title != title else (org_title or title)

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(self._back_img_url + (film.get("backdrop_path") or "")),
            title       = final_title,
            description = film.get("overview") or None,
            year        = (film.get("release_date", "") or "")[:4] or None,
            tags        = [g.get("name") for g in film.get("genres", [])],
            rating      = str(film.get("vote_average", "")),
            actors      = [c.get("name") for c in film.get("credits", {}).get("cast", [])][:10],
            duration    = film.get("runtime"),
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek      = await self.httpx.get(f"{self.main_url}/movie/{url}?api_key={self._api_key}&language=tr-TR")
        film       = istek.json()
        movie_name = film.get("original_title") or film.get("title", "")
        year       = int((film.get("release_date", "") or "0000")[:4] or 0)
        imdb_id    = film.get("imdb_id", "")

        try:
            api_istek = await self.httpx.get(
                self._api_url,
                params  = {"tmdb_id": url, "name": movie_name, "year": str(year), "imdb_id": imdb_id},
                timeout = 35,
            )
            veriler = api_istek.json()
            if not veriler.get("success"):
                return []

            results = []
            for sonuc in veriler.get("results", []):
                subtitles = [
                    self.new_subtitle(sub.get("file"), sub.get("label"))
                    for sub in sonuc.get("subtitles", [])
                ]
                results.append(ExtractResult(
                    name      = sonuc.get("name"),
                    url       = sonuc.get("url"),
                    referer   = sonuc.get("referer"),
                    subtitles = subtitles,
                ))
            return results
        except Exception:
            return []
