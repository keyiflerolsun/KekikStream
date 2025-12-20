# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
import re, json

class Odnoklassniki(ExtractorBase):
    name     = "Odnoklassniki"
    main_url = "https://odnoklassniki.ru"

    # Birden fazla domain destekle
    supported_domains = ["odnoklassniki.ru", "ok.ru"]

    def can_handle_url(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)

    async def extract(self, url, referer=None) -> ExtractResult:
        if "/video/" in url:
            url = url.replace("/video/", "/videoembed/")

        headers = {
            "Accept"         : "*/*",
            "Connection"     : "keep-alive",
            "Sec-Fetch-Dest" : "empty",
            "Sec-Fetch-Mode" : "cors",
            "Sec-Fetch-Site" : "cross-site",
            "Origin"         : self.main_url,
            "User-Agent"     : "Mozilla/5.0 (X11; Linux x86_64; rv:101.0) Gecko/20100101 Firefox/101.0",
        }
        self.httpx.headers.update(headers)

        try:
            istek = await self.fetch_with_redirects(url)
            istek.raise_for_status()
        except Exception as hata:
            raise RuntimeError(f"Failed to fetch the URL: {url}, Error: {hata}") from hata

        response_text = (
            istek.text.replace("\\&quot;", "\"")
                      .replace("\\\\", "\\")
                      .replace(r"\\u", "\\u")
        )
        response_text = re.sub(
            r"\\u([0-9A-Fa-f]{4})", 
            lambda match: chr(int(match[1], 16)), 
            response_text
        )

        videos_match = re.search(r'"videos":(\[.*?\])', response_text)
        if not videos_match:
            raise ValueError("No video data found in the response.")

        try:
            videos = json.loads(videos_match[1])
        except json.JSONDecodeError as hata:
            raise ValueError("Failed to parse video data.") from hata

        quality_order = {
            "ULTRA": 6,  # 4K veya daha yüksek
            "QUAD": 5,   # 1440p
            "FULL": 4,   # 1080p
            "HD": 3,     # 720p
            "SD": 2,     # 480p
            "LOW": 1,    # 360p
            "MOBILE": 0  # 144p
        }

        # Kaliteye göre en iyi videoyu seçme
        best_video = None
        best_quality_score = -1

        for video in videos:
            video_url    = video.get("url")
            quality_name = video.get("name", "").upper()

            if not video_url or not quality_name:
                continue

            # Kalite sıralamasına göre puanla
            quality_score = quality_order.get(quality_name, -1)
            if quality_score > best_quality_score:
                best_quality_score = quality_score
                best_video         = video_url

        if not best_video:
            raise ValueError("No valid video URLs found.")

        if best_video.startswith("//"):
            best_video = f"https:{best_video}"

        return ExtractResult(
            name       = self.name,
            url        = best_video,
            referer    = referer,
            user_agent = headers.get("User-Agent", None),
            subtitles  = []
        )

    async def fetch_with_redirects(self, url, max_redirects=5):
        """Yönlendirmeleri takip eden bir fonksiyon"""
        redirects = 0
        while redirects < max_redirects:
            istek = await self.httpx.get(url, follow_redirects=False)

            if istek.status_code not in [301, 302]:
                break  # Yönlendirme yoksa çık

            redirected_url = istek.headers.get("Location")
            if not redirected_url:
                raise ValueError("Redirect location not found.")

            url = redirected_url if redirected_url.startswith("http") else f"https://{redirected_url}"
            redirects += 1

        if redirects == max_redirects:
            raise RuntimeError(f"Max redirects ({max_redirects}) reached.")

        return istek