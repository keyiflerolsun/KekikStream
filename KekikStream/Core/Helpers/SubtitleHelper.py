# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from ..Extractor.ExtractorModels import Subtitle
import httpx

class SubtitleHelper:
    WYZIE_API     = "https://sub.wyzie.ru"
    WYZIE_API_KEY = "wyzie-2ed17f5e91a93b1a62022ba284d34719"
    OPEN_SUB_API  = "https://opensubtitles-v3.strem.io"

    @staticmethod
    async def fetch_external_subtitles(
        imdb_id: str | None = None,
        tmdb_id: str | None = None,
        season: int | None = None,
        episode: int | None = None
    ) -> list[Subtitle]:
        """Wyzie ve OpenSubtitles üzerinden altyazı çeker, Türkçe ve İngilizce ile sınırlandırır."""
        subtitles = []

        # Her iki API için de bir ID lazım
        target_id = imdb_id or tmdb_id
        if not target_id:
            return subtitles

        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            # 1. Wyzie API
            try:
                wyzie_subs = await SubtitleHelper._fetch_wyzie(client, target_id, season, episode)
                subtitles.extend(wyzie_subs)
            except Exception:
                pass

            # 2. OpenSubtitles (Stremio Addon)
            if imdb_id:
                try:
                    os_subs = await SubtitleHelper._fetch_opensubtitles(client, imdb_id, season, episode)
                    subtitles.extend(os_subs)
                except Exception:
                    pass

        # Türkçe ve İngilizce altyazıları filtrele ve her biri için en fazla 5 adet sakla
        import re
        turkish_subs = []
        english_subs = []

        for sub in subtitles:
            parts = sub.name.split("|")
            if len(parts) < 2:
                continue
            lang_part  = parts[1].strip().upper()
            lang_match = re.findall(r"^[A-Z]+", lang_part)
            if not lang_match:
                continue
            lang_code = lang_match[0]

            if lang_code in {"TR", "TUR", "TURKISH"}:
                if len(turkish_subs) < 2:
                    turkish_subs.append(sub)
            elif lang_code in {"EN", "ENG", "ENGLISH"}:
                if len(english_subs) < 2:
                    english_subs.append(sub)

        return turkish_subs + english_subs

    @staticmethod
    async def _fetch_wyzie(client: httpx.AsyncClient, target_id: str, season: int | None = None, episode: int | None = None) -> list[Subtitle]:
        params = {
            "id"  : target_id,
            "key" : SubtitleHelper.WYZIE_API_KEY
        }
        if season is not None:
            params["season"] = season
        if episode is not None:
            params["episode"] = episode

        resp = await client.get(f"{SubtitleHelper.WYZIE_API}/search", params=params)
        if resp.status_code != 200:
            return []

        data = resp.json()
        if not isinstance(data, list):
            return []

        results = []
        for item in data:
            url  = item.get("url")
            lang = item.get("lang") or item.get("language") or "Altyazı"
            if url:
                results.append(Subtitle(name=f"Wyzie | {lang.upper()}", url=url))
        return results

    @staticmethod
    async def _fetch_opensubtitles(client: httpx.AsyncClient, imdb_id: str, season: int | None = None, episode: int | None = None) -> list[Subtitle]:
        # Stremio addon formatı
        if season is None:
            url = f"{SubtitleHelper.OPEN_SUB_API}/subtitles/movie/{imdb_id}.json"
        else:
            url = f"{SubtitleHelper.OPEN_SUB_API}/subtitles/series/{imdb_id}:{season}:{episode}.json"

        resp = await client.get(url)
        if resp.status_code != 200:
            return []

        data    = resp.json()
        subs    = data.get("subtitles", [])
        results = []
        for item in subs:
            url  = item.get("url")
            lang = item.get("lang") or "Altyazı"
            if url:
                results.append(Subtitle(name=f"OpenSub | {lang.upper()}", url=url))
        return results
