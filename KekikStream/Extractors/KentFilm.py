# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper

class KentFilm(ExtractorBase):
    name     = "KentFilm"
    main_url = "https://kentfilmizle.xyz"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        istek  = await self.httpx.get(url, headers={"Referer": referer})
        helper = HTMLHelper(istek.text)

        # HTMLHelper.regex_first otomatik olarak ilk grubu döndürür
        json_str = helper.regex_first(r'FirePlayer\s*\(\s*[^,]+\s*,\s*(\{.*?\})\s*,')

        if not json_str:
            # Fallback regex explicit
            json_str = helper.regex_first(r'FirePlayer\s*\(\s*[^,]+\s*,\s*(\{.*?\})\s*,\s*false\s*\);')

        if not json_str:
            raise ValueError(f"KentFilm: Video bilgisi bulunamadı. {url}")

        try:
            # Extract videoUrl directly via regex to avoid JSON parsing issues
            # "videoUrl":"..."
            video_url = HTMLHelper(json_str).regex_first(r'"videoUrl"\s*:\s*"([^"]+)"')

            if not video_url:
                raise ValueError(f"KentFilm: Video URL bulunamadı. {url}")

            # Unescape forward slashes: \/ -> /
            video_url = video_url.replace("\\/", "/")

            # /cdn/hls/... -> https://kentfilmizle.xyz/cdn/hls/...
            if video_url.startswith("/"):
                video_url = f"{self.main_url}{video_url}"

            # Ek parametreleri al: videoServer (s) ve videoDisk (d)
            # "videoServer":"1"
            # "videoDisk":null veya "videoDisk":"..."
            video_server = HTMLHelper(json_str).regex_first(r'"videoServer"\s*:\s*"([^"]+)"')
            video_disk   = HTMLHelper(json_str).regex_first(r'"videoDisk"\s*:\s*"([^"]+)"')

            # Eğer disk bulunamazsa (null ise), boş string geçilebilir
            if not video_disk:
                video_disk = ""

            if video_server:
                video_url = f"{video_url}?s={video_server}&d={video_disk}"

            return ExtractResult(
                name       = self.name,
                url        = video_url,
                user_agent = self.httpx.headers.get("User-Agent"),
                referer    = url
            )
        except Exception as e:
            raise ValueError(f"KentFilm: Video bilgisi işlenirken hata oluştu. {url}") from e