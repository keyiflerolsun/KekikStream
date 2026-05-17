# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult

class TauVideo(ExtractorBase):
    name     = "TauVideo"
    main_url = "https://tau-video.xyz"

    async def extract(self, url: str, referer: str | None = None) -> ExtractResult | list[ExtractResult] | None:
        headers = {"Referer": referer or self.main_url}

        # Extract video key, handle query params if present
        # /embed/ID?vid=... -> ID?vid=...
        video_key = url.rstrip("/").split("/")[-1]
        api_url   = f"{self.main_url}/api/video/{video_key}"

        # Cloudflare bypasslı GET
        response = await self.async_cf_get(api_url, headers=headers)

        try:
            api_data = response.json()
        except Exception:
             raise ValueError(f"TauVideo: API yanıtı JSON değil. {url}")

        if "urls" not in api_data:
            raise ValueError(f"TauVideo: API yanıtında 'urls' bulunamadı. {url}")

        results = []
        for video in api_data["urls"]:
            file_url = video.get("url")
            label    = video.get("label", "Kaynak")
            if file_url:
                results.append(ExtractResult(
                    name      = f"{self.name} | {label}",
                    url       = self.fix_url(file_url),
                    referer   = self.main_url,
                    subtitles = []
                ))

        if not results:
            return None

        return results
