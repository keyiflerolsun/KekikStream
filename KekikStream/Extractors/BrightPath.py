# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
import re, json, base64, gzip

class BrightPath(ExtractorBase):
    name     = "BrightPath"
    main_url = "https://brightpathsignals.com"

    supported_domains = [
        "brightpathsignals.com",
        "vaplayer.ru",
        "remoteconsultinggroup.site"
    ]

    def _decode_stream_url(self, data: str) -> str:
        try:
            # Clean and add padding
            cleaned = data.replace(".", "+").replace("_", "/")
            cleaned += "=" * (4 - len(cleaned) % 4) if len(cleaned) % 4 else ""

            # Base64 decode and Gzip decompress
            decoded = base64.b64decode(cleaned)
            return gzip.decompress(decoded).decode()
        except Exception:
            return data

    async def extract(self, url: str, referer: str = None) -> list[ExtractResult]:
        # If it's already a decoded stream URL (m3u8), return it
        if ".m3u8" in url or ".mp4" in url:
            return [ExtractResult(name=self.name, url=url, referer=referer)]

        # Fetch the embed page
        istek  = await self.async_cf_get(url, headers={"Referer": referer or self.main_url})
        secici = HTMLHelper(istek.text)

        # Extract config from the page
        config_raw = secici.regex_first(r"const CONFIG = ({.*?});")
        if not config_raw:
            raise ValueError(f"BrightPath: Config bulunamadı. {url}")

        config = json.loads(config_raw)

        # Determine API parameters
        media_id   = config.get("mediaId")
        id_type    = config.get("idType", "tmdb")
        media_type = config.get("mediaType", "movie")
        season     = config.get("season")
        episode    = config.get("episode")

        api_url = config.get("streamDataApiUrl", "https://streamdata.vaplayer.ru/api.php")

        params = {
            id_type : media_id,
            "type"  : media_type
        }
        if season:
            params["season"] = season
        if episode:
            params["episode"] = episode

        # Call the API
        api_headers = {
            "Referer"          : url,
            "X-Requested-With" : "XMLHttpRequest"
        }
        api_istek = await self.async_cf_get(api_url, params=params, headers=api_headers)
        api_data  = api_istek.json()

        if api_data.get("status_code") != "200" or "data" not in api_data:
             raise ValueError(f"BrightPath: API hatası. {api_data.get('message', 'Unknown error')}")

        results     = []
        stream_urls = api_data["data"].get("stream_urls", [])

        # Subtitles
        subtitles = []
        seen_urls = set()

        def add_subtitle(url, name):
            full_url = self.fix_url(url)
            if full_url and full_url not in seen_urls:
                subtitles.append(Subtitle(url=full_url, name=name))
                seen_urls.add(full_url)

        # 1. External Subtitle (from data or config)
        ext_sub = api_data["data"].get("externalSub") or config.get("externalSub")
        if ext_sub and ext_sub.get("file"):
            add_subtitle(
                url  = ext_sub["file"],
                name = ext_sub.get("label") or ext_sub.get("lang") or "Subtitle"
            )

        # 2. Default Subtitles (from root)
        for sub in api_data.get("default_subs", []):
            add_subtitle(
                url  = sub["url"],
                name = sub.get("lang") or "Subtitle"
            )

        # 3. Subtitles from data
        for sub in api_data["data"].get("subtitles", []):
            add_subtitle(
                url  = sub.get("file") or sub.get("url"),
                name = sub.get("label") or sub.get("lang") or "Subtitle"
            )

        for idx, s_url in enumerate(stream_urls, 1):
            # If it's a list, the first item is the name, second is the URL
            if isinstance(s_url, list) and len(s_url) >= 2:
                name = s_url[0]
                link = self._decode_stream_url(s_url[1])
            else:
                name = f"Source {idx}"
                link = self._decode_stream_url(s_url)

            # Avoid "BrightPath | BrightPath" or "BrightPath | Source X" duplication
            # if the name is already the extractor name or a generic Source X.
            # Actually, keeping Source X is fine, but "BrightPath | BrightPath" is ugly.
            display_name = name
            if display_name.lower() == self.name.lower():
                display_name = f"Source {idx}"

            results.append(ExtractResult(
                name      = f"{self.name} | {display_name}",
                url       = link,
                referer   = url,
                subtitles = subtitles
            ))

        return results
