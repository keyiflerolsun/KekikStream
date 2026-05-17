# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from typing import TYPE_CHECKING
import httpx, re

if TYPE_CHECKING:
    from ..Plugin.PluginModels import MovieInfo, SeriesInfo

class MetadataHelper:
    TMDB_API_KEY = "84259f99204eeb7d45c7e3d8e36c6123"
    TMDB_BASE    = "https://api.themoviedb.org/3"
    IMG_BASE     = "https://image.tmdb.org/t/p/w500"

    @staticmethod
    async def enrich_metadata(info: "MovieInfo" | "SeriesInfo") -> "MovieInfo" | "SeriesInfo":
        """Eksik metadataları TMDB üzerinden tamamlar."""
        from ..Plugin.PluginModels import SeriesInfo
        is_series  = isinstance(info, SeriesInfo)
        media_type = "tv" if is_series else "movie"

        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            # Sezon bilgisini başlıktan çıkar ve başlığı temizle (Eğer dizi ise)
            parsed_season = None
            search_title  = info.title
            if is_series and info.title:
                clean_title_no_season, parsed_season = MetadataHelper.extract_season_from_title(info.title)
                search_title = clean_title_no_season
                if parsed_season and info.episodes:
                    for ep in info.episodes:
                        if not ep.season or ep.season == 1:
                            ep.season = parsed_season

            # 1. ID'ler yoksa Title ve Year ile TMDB'de ara
            tmdb_id = info.tmdb_id
            if not tmdb_id and not info.imdb_id and info.title:
                try:
                    searched_id = await MetadataHelper._search_tmdb_id(client, search_title, info.year, is_series)
                    if searched_id:
                        tmdb_id = searched_id
                except Exception:
                    pass

            # 2. TMDB ID yoksa ama IMDB ID varsa onunla bul
            if not tmdb_id and info.imdb_id:
                tmdb_id = await MetadataHelper._find_tmdb_id(client, info.imdb_id)

            if not tmdb_id:
                return info

            # 2. Detayları çek
            try:
                details = await MetadataHelper._fetch_details(client, tmdb_id, media_type)
                if not details:
                    return info

                # Eksik alanları doldur
                if not info.description:
                    info.description = details.get("overview")

                if not info.poster or "favicons" in info.poster:
                    poster_path = details.get("poster_path") or details.get("backdrop_path")
                    if poster_path:
                        info.poster = f"{MetadataHelper.IMG_BASE}{poster_path}"

                if not info.year:
                    date_key  = "first_air_date" if is_series else "release_date"
                    info.year = (details.get(date_key) or "")[:4] or None

                if not info.rating or info.rating == "0.0":
                    info.rating = str(details.get("vote_average", ""))

                if not info.tags:
                    info.tags = ", ".join([g.get("name") for g in details.get("genres", [])])

                if not info.duration and not is_series:
                    info.duration = details.get("runtime")

                if not info.actors:
                    credits     = details.get("credits", {})
                    cast        = credits.get("cast", [])
                    info.actors = ", ".join([c.get("name") for c in cast[:10]])

                # ID'leri güncelle
                info.tmdb_id = str(tmdb_id)
                if not info.imdb_id:
                    info.imdb_id = details.get("imdb_id") or details.get("external_ids", {}).get("imdb_id")

                # 3. Eğer dizi ise ve TMDB ID'si varsa, bölümlerin isimlerini zenginleştir
                if is_series and info.episodes:
                    try:
                        await MetadataHelper.enrich_episodes(client, tmdb_id, info.episodes)
                    except Exception as e:
                        from ...CLI import konsol
                        konsol.log(f"[yellow][!] TMDB Bölüm Zenginleştirme Hatası: {e}[/]")

            except Exception as e:
                from ...CLI import konsol
                konsol.log(f"[yellow][!] TMDB Zenginleştirme Hatası: {e}[/]")

        return info

    @staticmethod
    async def _find_tmdb_id(client: httpx.AsyncClient, imdb_id: str) -> str | None:
        """IMDB ID kullanarak TMDB ID bulur."""
        url  = f"{MetadataHelper.TMDB_BASE}/find/{imdb_id}"
        resp = await client.get(url, params={"api_key": MetadataHelper.TMDB_API_KEY, "external_source": "imdb_id"})
        if resp.status_code == 200:
            data = resp.json()
            # find endpoint'i results döner
            movie_results = data.get("movie_results", [])
            tv_results    = data.get("tv_results", [])
            if movie_results:
                return str(movie_results[0].get("id"))
            if tv_results:
                return str(tv_results[0].get("id"))
        return None

    @staticmethod
    async def _fetch_details(client: httpx.AsyncClient, tmdb_id: str, media_type: str) -> dict | None:
        """TMDB üzerinden detaylı bilgi çeker."""
        url    = f"{MetadataHelper.TMDB_BASE}/{media_type}/{tmdb_id}"
        params = {
            "api_key"            : MetadataHelper.TMDB_API_KEY,
            "language"           : "tr-TR",
            "append_to_response" : "credits,external_ids"
        }
        resp = await client.get(url, params=params)
        if resp.status_code == 200:
            return resp.json()
        return None

    @staticmethod
    async def _search_tmdb_id(client: httpx.AsyncClient, title: str, year: str | None, is_series: bool) -> str | None:
        """Başlık ve yıla göre TMDB ID'si arar."""
        media_type = "tv" if is_series else "movie"
        url        = f"{MetadataHelper.TMDB_BASE}/search/{media_type}"

        # Başlıktaki parantez içi veya ek bilgileri temizlemeye çalışalım
        # Örneğin: "Örümcek-Adam: Eve Dönüş Yok (2021)" -> "Örümcek-Adam: Eve Dönüş Yok"
        clean_title = re.sub(r"\s*[\(\[\{].*?[\)\]\}]", "", title).strip()
        # Türkçe dublaj/altyazı izle gibi eklentilere özgü ibareleri temizle
        clean_title = re.sub(
            r"\s+(?:türkçe\s+dublaj|altyazılı|dublaj|izle|full\s+hd|hd)\b",
            "",
            clean_title,
            flags=re.IGNORECASE
        ).strip()
        if not clean_title:
            clean_title = title

        params = {
            "api_key"  : MetadataHelper.TMDB_API_KEY,
            "query"    : clean_title,
            "language" : "tr-TR"
        }

        if year:
            year_key = "first_air_date_year" if is_series else "primary_release_year"
            params[year_key] = str(year)[:4]

        resp = await client.get(url, params=params)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            if results:
                return str(results[0].get("id"))

        # Eğer yıl ile sonuç bulunamadıysa, yıl parametresi olmadan tekrar dene
        if year and len(params) > 3:
            params.pop("first_air_date_year" if is_series else "primary_release_year", None)
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if results:
                    return str(results[0].get("id"))

        return None

    @staticmethod
    def extract_season_from_title(title: str) -> tuple[str, int | None]:
        """Başlıktan sezon bilgisini ayıklar ve temiz başlığı döner."""
        # Arama kalıpları: "3. Sezon", "Sezon 3", "Season 2", "2.Sezon"
        pattern = r"\s*\(?\b(?:(\d+)(?:\.|th|rd|nd|st)?\s*(?:sezon|season)|(?:sezon|season)\s*(\d+))\b\)?"
        match   = re.search(pattern, title, flags=re.IGNORECASE)
        if match:
            season = int(match.group(1) or match.group(2))
            # Eşleşen kısmı başlıktan çıkar
            clean = re.sub(pattern, "", title, flags=re.IGNORECASE).strip()
            # Kalan boşlukları ve tireleri temizle (örn: "Dizi Adi - " -> "Dizi Adi")
            clean = re.sub(r"\s*-\s*$", "", clean).strip()
            return clean, season
        return title, None

    @staticmethod
    async def enrich_episodes(client: httpx.AsyncClient, tmdb_id: str, episodes: list):
        """Dizi bölümlerinin isimlerini TMDB üzerinden tamamlar/zenginleştirir."""
        import asyncio
        # Benzersiz sezon numaralarını belirle (Sezon bilgisi yoksa veya None ise 1 varsayabiliriz)
        seasons = {ep.season or 1 for ep in episodes}

        # Her sezon için TMDB'den bölüm detaylarını paralel çek
        tasks = {
            season: MetadataHelper._fetch_season_details(client, tmdb_id, season)
            for season in seasons
        }

        # Görevleri çalıştır ve sonuçları eşle
        season_keys = list(tasks.keys())
        results     = await asyncio.gather(*[tasks[s] for s in season_keys], return_exceptions=True)

        seasons_data = {}
        for season, res in zip(season_keys, results):
            if isinstance(res, dict) and "episodes" in res:
                seasons_data[season] = res["episodes"]

        # Eğer yüksek sezonlar bulunamadıysa (None/404) ve Season 1 çekilmediyse, Season 1'i yedek olarak çek
        missing_high_seasons = [s for s in seasons if s > 1 and s not in seasons_data]
        if missing_high_seasons and 1 not in seasons_data:
            try:
                s1_data = await MetadataHelper._fetch_season_details(client, tmdb_id, 1)
                if s1_data and "episodes" in s1_data:
                    seasons_data[1] = s1_data["episodes"]
            except Exception:
                pass

        # Bölüm listesini güncelle
        for ep in episodes:
            season_num = ep.season or 1
            ep_num     = ep.episode
            if not ep_num:
                continue

            match = None
            # 1. Doğrudan kendi sezonunda ara
            if season_num in seasons_data:
                match = next((item for item in seasons_data[season_num] if item.get("episode_number") == ep_num), None)

            # 2. Kendi sezonunda bulunamadıysa ve Season 1 yedek listesi varsa mutlak bölüm olarak ara
            if not match and 1 in seasons_data:
                match = next((item for item in seasons_data[1] if item.get("episode_number") == ep_num), None)

            # 3. Hala bulunamadıysa ve sezon > 1 ise, orijinal başlıktan mutlak bölüm numarasını ayıklamayı dene
            if not match and season_num > 1 and ep.title and 1 in seasons_data:
                abs_match = re.search(r"\b(\d+)\s*(?:\.|\b)\s*(?:bölüm|episode|capitulo|b\.?)\b", ep.title, flags=re.IGNORECASE)
                if abs_match:
                    abs_ep_num = int(abs_match.group(1))
                    match      = next((item for item in seasons_data[1] if item.get("episode_number") == abs_ep_num), None)

            if match:
                tmdb_title = match.get("name")
                if tmdb_title:
                    current_title = ep.title or ""

                    # Başlık jenerik mi veya boş mu kontrolü
                    is_generic = False
                    if not current_title:
                        is_generic = True
                    else:
                        normalized = current_title.lower()
                        # Eğer sadece bölüm/bölüm numarası barındırıyorsa jeneriktir
                        # örn: "1. bölüm", "bölüm 1", "episode 1", "1. sezon 1. bölüm"
                        # veya "1. bölüm izle" veya "capitulo 12"
                        if re.match(r"^(?:\d+[\.\-\s]*(?:bölüm|sezon|capitulo|episode|b\.?)|episode\s*\d+|capitulo\s*\d+|\d+)$", normalized) or "izle" in normalized:
                            is_generic = True

                    normalized_tmdb = tmdb_title.lower()
                    is_tmdb_generic = bool(re.match(r"^(?:\d+[\.\-\s]*(?:bölüm|sezon|capitulo|episode|b\.?)|episode\s*\d+|capitulo\s*\d+|\d+)$", normalized_tmdb))

                    if is_generic:
                        if is_tmdb_generic:
                            ep.title = f"{ep_num}. Bölüm"
                        else:
                            ep.title = f"{ep_num}. Bölüm - {tmdb_title}"
                    else:
                        if not is_tmdb_generic and tmdb_title.lower() not in current_title.lower():
                            ep.title = f"{current_title} - {tmdb_title}"

    @staticmethod
    async def _fetch_season_details(client: httpx.AsyncClient, tmdb_id: str, season: int) -> dict | None:
        """TMDB üzerinden belirli bir sezonun detaylarını (bölümleri) çeker."""
        url    = f"{MetadataHelper.TMDB_BASE}/tv/{tmdb_id}/season/{season}"
        params = {
            "api_key"  : MetadataHelper.TMDB_API_KEY,
            "language" : "tr-TR"
        }
        resp = await client.get(url, params=params)
        if resp.status_code == 200:
            return resp.json()
        return None
