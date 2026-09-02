# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from .TitleHelper import clean_title, clean_episode_title, GENERIC_EPISODE_TITLE, SEASON_IN_TITLE
import asyncio, difflib, re, httpx


class MetadataHelper:
    """TMDB'den yalnızca güvenilir biçimde eksik kalan metadata'yı tamamlar."""

    TMDB_API_KEY         = "84259f99204eeb7d45c7e3d8e36c6123"
    TMDB_BASE            = "https://api.themoviedb.org/3"
    IMG_BASE             = "https://image.tmdb.org/t/p/w500"
    SIMILARITY_THRESHOLD = 0.45

    # Bölüm-başlığı temizliği tek kaynak: `TitleHelper` (re-export).
    clean_episode_title = staticmethod(clean_episode_title)

    @staticmethod
    async def _request_json(client: httpx.AsyncClient, url: str, params: dict) -> dict | None:
        """Beklenen ağ ve bozuk JSON hatalarını tek sınırda ele al."""
        try:
            response = await client.get(url, params=params)
            data     = response.json() if response.status_code == 200 else None
        except (httpx.HTTPError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    @staticmethod
    async def enrich_metadata(info, lang: str = "tr-TR"):
        """Eksik alanları tamamla; belirsiz eşleşmede öğeyi değiştirme."""
        from ..Plugin.PluginModels import SeriesInfo

        is_series    = isinstance(info, SeriesInfo)
        try:
            search_title = info.title
            if is_series and info.title:
                search_title, season = MetadataHelper.extract_season_from_title(info.title)
                if season and info.episodes:
                    for episode in info.episodes:
                        if episode.season in (None, 1):
                            episode.season = season

            async with httpx.AsyncClient(timeout=3, follow_redirects=True) as client:
                tmdb_id = await MetadataHelper._resolve_tmdb_id(client, info, search_title, is_series, lang)
                if not tmdb_id:
                    return info

                details = await MetadataHelper._fetch_details(client, tmdb_id, "tv" if is_series else "movie", lang)
                if not details:
                    return info

                MetadataHelper._merge_details(info, details, tmdb_id, is_series)
                if is_series and info.episodes:
                    await MetadataHelper.enrich_episodes(client, tmdb_id, info.episodes, lang, details)
                    for episode in info.episodes:
                        episode.title = clean_episode_title(info.title, episode.title)

            return info
        finally:
            # `Episode` modeli başlık yoksa bunu None olarak korur; TMDB denemesi
            # bittikten sonra hâlâ karşılığı olmayan bölümler için sadece gösterim
            # fallback'i üret. Bunu model doğrulamasında yapmak, TMDB'nin gerçek
            # başlık doldurma yolunu `1x2` ile yanlışlıkla kapatıyordu.
            if is_series:
                MetadataHelper._apply_episode_title_fallbacks(info.episodes)

    @staticmethod
    def _apply_episode_title_fallbacks(episodes: list | None) -> None:
        """TMDB/source adı olmayan numaralı bölümlere kararlı ekran etiketi ver."""
        for episode in episodes or []:
            if not episode.title and episode.episode:
                episode.title = f"{episode.season or 1}x{episode.episode}"

    @staticmethod
    async def _resolve_tmdb_id(client: httpx.AsyncClient, info, title: str | None, is_series: bool, lang: str) -> str | None:
        if info.tmdb_id:
            return str(info.tmdb_id)
        if info.imdb_id:
            return await MetadataHelper._find_tmdb_id(client, info.imdb_id)
        return await MetadataHelper._search_tmdb_id(client, title, info.year, is_series, lang) if title else None

    @staticmethod
    def _merge_details(info, details: dict, tmdb_id: str, is_series: bool) -> None:
        if not info.description:
            info.description = details.get("overview") or None
        if not info.poster or "favicons" in info.poster:
            if poster_path := details.get("poster_path") or details.get("backdrop_path"):
                info.poster = f"{MetadataHelper.IMG_BASE}{poster_path}"
        if not info.year:
            info.year = (details.get("first_air_date" if is_series else "release_date") or "")[:4] or None
        if not info.rating and (rating := details.get("vote_average")):
            info.rating = str(rating)
        if not info.tags:
            info.tags = ", ".join(genre["name"] for genre in details.get("genres", []) if genre.get("name")) or None
        if not info.duration and not is_series:
            info.duration = details.get("runtime") or None
        if not info.actors:
            cast        = details.get("credits", {}).get("cast", [])
            info.actors = ", ".join(person["name"] for person in cast[:10] if person.get("name")) or None

        info.tmdb_id = str(tmdb_id)
        if not info.imdb_id:
            info.imdb_id = details.get("imdb_id") or details.get("external_ids", {}).get("imdb_id")

    @staticmethod
    async def _find_tmdb_id(client: httpx.AsyncClient, imdb_id: str) -> str | None:
        data = await MetadataHelper._request_json(client, f"{MetadataHelper.TMDB_BASE}/find/{imdb_id}", {
            "api_key": MetadataHelper.TMDB_API_KEY, "external_source": "imdb_id",
        })
        if not data:
            return None
        for key in ("movie_results", "tv_results"):
            if results := data.get(key):
                return str(results[0]["id"]) if results[0].get("id") else None
        return None

    @staticmethod
    async def _fetch_details(client: httpx.AsyncClient, tmdb_id: str, media_type: str, lang: str) -> dict | None:
        return await MetadataHelper._request_json(client, f"{MetadataHelper.TMDB_BASE}/{media_type}/{tmdb_id}", {
            "api_key": MetadataHelper.TMDB_API_KEY, "language": lang, "append_to_response": "credits,external_ids",
        })

    @staticmethod
    async def _search_tmdb_id(client: httpx.AsyncClient, title: str, year: str | None, is_series: bool, lang: str) -> str | None:
        # SEO/dil suffix temizliği için ortak `clean_title` (TitleHelper tek kaynak);
        # TMDB araması ayrıca parantez içi bilgiyi (yıl, orijinal ad) ve çıplak
        # kalite etiketini de atar.
        base  = clean_title(title) or title
        query = re.sub(r"\s*[\(\[\{].*?[\)\]\}]", "", base)
        query = re.sub(r"\s+\b(?:hd|fhd|uhd|sd|4k)\b", "", query, flags=re.I).strip() or base

        # Başlıkta parantezsiz bir yıl geçiyorsa: ayrı bir yıl yoksa onu kullan;
        # zaten biliniyorsa başlıktan sil (tekrar eden yıl TMDB aramasını bozuyor,
        # ör. "Training Day 2001" → "Training Day" + year=2001). "Blade Runner 2049"
        # gibi yılın adın parçası olduğu durumlar korunur (yıl eşleşmez / bilinmez).
        if match := re.search(r"\b(19|20)\d{2}\b", query):
            title_year = match.group(0)
            if not year:
                year = title_year
            if year and str(year)[:4] == title_year:
                query = query[:match.start()] + query[match.end():]

        query  = re.sub(r"\s{2,}", " ", query).strip(" -–—:|") or title
        params = {"api_key": MetadataHelper.TMDB_API_KEY, "query": query, "language": lang}
        if year:
            params["first_air_date_year" if is_series else "primary_release_year"] = str(year)[:4]

        for include_year in (True, False) if year else (True,):
            request_params = params if include_year else {key: value for key, value in params.items() if not key.endswith("_year")}
            data           = await MetadataHelper._request_json(client, f"{MetadataHelper.TMDB_BASE}/search/{'tv' if is_series else 'movie'}", request_params)
            if data and (best := MetadataHelper._pick_best_result(data.get("results", []), query, year)):
                return str(best["id"])
        return None

    @staticmethod
    def _pick_best_result(results: list, title: str, year: str | None) -> dict | None:
        title_key = title.casefold().strip()
        year_key  = str(year)[:4] if year else None
        scores    = []
        for result in results[:5]:
            # `language=tr-TR` altında `title`/`name` yerelleştirilmiş gelir;
            # sorgu çoğu zaman orijinal/İngilizce ad olduğundan `original_*` ile
            # de karşılaştır, en iyi eşleşmeyi al ("Training Day" ⟷ "İlk Gün").
            candidates = [
                (result.get("title") or result.get("name") or "").casefold().strip(),
                (result.get("original_title") or result.get("original_name") or "").casefold().strip(),
            ]
            # `language=tr-TR` altında `title` yerelleşir; sorgu çoğu zaman orijinal
            # ad olduğundan `original_*` ile de kıyasla, en iyi ORAN'ı temel al.
            title_ratio = max(
                (difflib.SequenceMatcher(None, title_key, cand).ratio() for cand in candidates if cand),
                default=0.0,
            )
            result_year = (result.get("release_date") or result.get("first_air_date") or "")[:4]
            year_bonus  = 0.0
            if year_key and year_key.isdigit() and result_year.isdigit():
                difference = abs(int(result_year) - int(year_key))
                # A fallback search without `*_year` can otherwise match a
                # similarly named but decades-old work and overwrite empty
                # source metadata with a confidently wrong TMDB record.
                if difference > 1:
                    continue
                year_bonus = 0.15 if difference == 0 else 0.05
            scores.append((title_ratio, year_bonus, result))
        if not scores:
            return None
        # Sıralama title-oranı + yıl bonusuyla; KABUL yalnız title-oranıyla —
        # yıl, zayıf bir başlık eşleşmesini eşiğin üstüne itmemeli (yoksa
        # "The Movie" (2019) → yanlış filme bağlanır).
        title_ratio, year_bonus, result = max(scores, key=lambda item: item[0] + item[1])
        threshold = max(MetadataHelper.SIMILARITY_THRESHOLD, 0.65) if year_key else MetadataHelper.SIMILARITY_THRESHOLD
        return result if title_ratio >= threshold else None

    @staticmethod
    def extract_season_from_title(title: str) -> tuple[str, int | None]:
        if not (match := SEASON_IN_TITLE.search(title)):
            return title, None
        season = int(match.group(1) or match.group(2))
        return SEASON_IN_TITLE.sub("", title).rstrip(" -").strip(), season

    @staticmethod
    async def enrich_episodes(client: httpx.AsyncClient, tmdb_id: str, episodes: list, lang: str, details: dict | None = None) -> None:
        seasons   = sorted({episode.season or 1 for episode in episodes})
        data      = await asyncio.gather(*(MetadataHelper._fetch_season_details(client, tmdb_id, season, lang) for season in seasons))
        by_season = {season: value.get("episodes", []) for season, value in zip(seasons, data) if value and value.get("episodes")}

        # Gerçek sezonların (season_number > 0) kümülatif bölüm sayısı — plugin
        # MUTLAK bölüm no'su ("Episode 1000") kazıdıysa bunu gerçek S×E'ye çevirmek
        # için. `details` zaten çekilmişti; ekstra çağrı yok, sadece eşleşmeyen
        # bölümler için tek bir /season/{N} isteği.
        real_seasons = sorted(
            ((s.get("season_number"), s.get("episode_count") or 0)
             for s in (details or {}).get("seasons", []) if (s.get("season_number") or 0) > 0),
            key=lambda x: x[0] or 0,
        )
        abs_cache: dict[int, list] = {}

        async def _resolve_absolute(abs_no: int) -> dict | None:
            offset = 0
            for s_num, s_count in real_seasons:
                if abs_no <= offset + s_count:
                    if s_num not in abs_cache:
                        got = await MetadataHelper._fetch_season_details(client, tmdb_id, s_num, lang)
                        abs_cache[s_num] = (got or {}).get("episodes", [])
                    per_season = abs_no - offset
                    # TMDB bazı dizilerde (One Piece) sezon içinde de MUTLAK
                    # numara kullanıyor; her iki biçimi de dene.
                    return next(
                        (e for e in abs_cache[s_num]
                         if e.get("episode_number") in (abs_no, per_season)),
                        None,
                    )
                offset += s_count
            return None

        for episode in episodes:
            if not episode.episode:
                continue
            match = next((item for item in by_season.get(episode.season or 1, []) if item.get("episode_number") == episode.episode), None)
            if not match and real_seasons and episode.episode > (real_seasons[0][1] or 0):
                match = await _resolve_absolute(episode.episode)
            if not match or not (tmdb_title := match.get("name")):
                continue
            if not episode.title or GENERIC_EPISODE_TITLE.fullmatch(episode.title):
                episode.title = tmdb_title

    @staticmethod
    async def _fetch_season_details(client: httpx.AsyncClient, tmdb_id: str, season: int, lang: str) -> dict | None:
        return await MetadataHelper._request_json(client, f"{MetadataHelper.TMDB_BASE}/tv/{tmdb_id}/season/{season}", {
            "api_key": MetadataHelper.TMDB_API_KEY, "language": lang,
        })
