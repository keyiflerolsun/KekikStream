# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
import re, json

class TRsTX(ExtractorBase):
    name     = "TRsTX"
    main_url = "https://trstx.org"

    async def extract(self, url, referer=None) -> list[ExtractResult]:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        istek = await self.httpx.get(url)
        istek.raise_for_status()

        file_match = re.search(r'file\":\"([^\"]+)', istek.text)
        if not file_match:
            raise ValueError("File not found in response.")

        file_path = file_match[1].replace("\\", "")
        post_link = f"{self.main_url}/{file_path}"

        post_istek = await self.httpx.post(post_link)
        post_istek.raise_for_status()

        try:
            post_json = json.loads(post_istek.text)
        except json.JSONDecodeError as hata:
            raise ValueError("Failed to parse JSON response.") from hata

        video_data_list = post_json[1:] if isinstance(post_json, list) else []

        video_links = set()
        all_results = []

        for item in video_data_list:
            title = item.get("title")
            file  = item.get("file")

            if not title or not file:
                continue

            playlist_url = f"{self.main_url}/playlist/{file.lstrip('/')}.txt"
            playlist_request = await self.httpx.post(playlist_url, headers={"Referer": referer or self.main_url})
            playlist_request.raise_for_status()

            video_data = playlist_request.text

            if video_data in video_links:
                continue

            video_links.add(video_data)

            all_results.append(
                ExtractResult(
                    name      = f"{self.name} - {title}",
                    url       = video_data,
                    referer   = self.main_url,
                    headers   = {},
                    subtitles = []
                )
            )

        if not all_results:
            raise ValueError("No videos found in response.")

        return all_results[0] if len(all_results) == 1 else all_results