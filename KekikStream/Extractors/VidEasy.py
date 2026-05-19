# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
from urllib.parse     import urlparse, quote
import asyncio

class VidEasy(ExtractorBase):
    name              = "VidEasy"
    main_url          = "https://player.videasy.net"
    supported_domains = ["player.videasy.net", "videasy.net"]

    async def extract(self, url: str, referer: str = None) -> list[ExtractResult]:
        parsed     = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")

        media_type = "movie"
        tmdb_id    = None
        season     = None
        episode    = None

        if "tv" in path_parts:
            media_type = "tv"
            idx        = path_parts.index("tv")
            if len(path_parts) > idx + 1:
                tmdb_id = path_parts[idx + 1]
            if len(path_parts) > idx + 2:
                season = path_parts[idx + 2]
            if len(path_parts) > idx + 3:
                episode = path_parts[idx + 3]
        elif "movie" in path_parts:
            media_type = "movie"
            idx        = path_parts.index("movie")
            if len(path_parts) > idx + 1:
                tmdb_id = path_parts[idx + 1]

        if not tmdb_id:
            raise ValueError(f"Videasy: tmdb_id bulunamadı. {url}")

        # Fetch metadata from db.videasy.net proxy
        meta_url  = f"https://db.videasy.net/3/{media_type}/{tmdb_id}"
        meta_resp = await self.httpx.get(meta_url)
        meta_data = meta_resp.json()

        title = meta_data.get("title") or meta_data.get("name")
        if not title:
            raise ValueError(f"Videasy: metadata title bulunamadı. {url}")

        year_str = meta_data.get("release_date") or meta_data.get("first_air_date") or ""
        year     = year_str.split("-")[0] if "-" in year_str else ""

        imdb_id = None
        if media_type == "movie":
            imdb_id = meta_data.get("imdb_id")
        else:
            ext_url  = f"https://db.videasy.net/3/tv/{tmdb_id}/external_ids"
            ext_resp = await self.httpx.get(ext_url)
            if ext_resp.status_code == 200:
                imdb_id = ext_resp.json().get("imdb_id")

        enc_title = quote(quote(title))

        servers = [
            "myflixerzupcloud",
            "1movies",
            "moviebox",
            "primewire",
            "m4uhd",
            "hdmovie",
            "cdn",
            "primesrcme",
            "visioncine",
            "overflix",
            "superflix",
            "cuevana",
            "lamovie",
            "mb-flix"
        ]

        headers = {
            "Accept"     : "*/*",
            "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "Origin"     : "https://www.cineby.sc",
            "Referer"    : "https://www.cineby.sc/"
        }

        results = []

        async def fetch_server_sources(server: str):
            try:
                if media_type == "movie":
                    api_url = f"https://api.videasy.net/{server}/sources-with-title?title={enc_title}&mediaType=movie&year={year}&tmdbId={tmdb_id}&imdbId={imdb_id or ''}"
                else:
                    api_url = f"https://api.videasy.net/{server}/sources-with-title?title={enc_title}&mediaType=tv&year={year}&tmdbId={tmdb_id}&episodeId={episode}&seasonId={season}&imdbId={imdb_id or ''}"

                resp = await self.httpx.get(api_url, headers=headers)
                if resp.status_code != 200:
                    return

                enc_data = resp.text
                dec_url  = "https://enc-dec.app/api/dec-videasy"
                payload  = {"text": enc_data, "id": int(tmdb_id)}

                dec_resp = await self.httpx.post(dec_url, json=payload)
                if dec_resp.status_code != 200:
                    return

                res_data = dec_resp.json()
                result   = res_data.get("result", {})

                subtitles = []
                for sub in result.get("subtitles", []):
                    sub_url  = sub.get("url")
                    sub_lang = sub.get("language")
                    if sub_url and sub_lang:
                        subtitles.append(Subtitle(name=sub_lang, url=sub_url))

                for src in result.get("sources", []):
                    src_url = src.get("url")
                    quality = src.get("quality", "Auto")
                    if src_url:
                        results.append(ExtractResult(
                            name          = f"VidEasy [{server.upper()}] - {quality}",
                            url           = src_url,
                            referer       = "https://www.cineby.sc/",
                            user_agent    = headers["User-Agent"],
                            extra_headers = {"Origin": "https://www.cineby.sc"},
                            subtitles     = subtitles,
                            extractor     = self.name
                        ))
            except Exception:
                pass

        await asyncio.gather(*(fetch_server_sources(s) for s in servers))
        return results
