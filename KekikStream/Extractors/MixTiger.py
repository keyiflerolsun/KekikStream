# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult

class MixTiger(ExtractorBase):
    name     = "MixTiger"
    main_url = "https://www.mixtiger.com"

    async def extract(self, url, referer=None) -> ExtractResult:
        ext_ref  = referer or ""
        post_url = f"{url}?do=getVideo"
        vid_id   = url.split("video/")[-1] if "video/" in url else ""

        response = await self.cffi.post(
            url     = post_url,
            data    = {"hash": vid_id, "r": ext_ref, "s": ""},
            headers = {
                "Referer"          : ext_ref,
                "Content-Type"     : "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With" : "XMLHttpRequest"
            }
        )
        response.raise_for_status()

        video_data = response.json()

        # videoSrc varsa doğrudan kullan
        if video_data.get("videoSrc"):
            m3u_link = video_data["videoSrc"]
        # videoSources listesi varsa son elemanı al
        elif video_data.get("videoSources"):
            sources  = video_data["videoSources"]
            m3u_link = sources[-1].get("file") if sources else None
        else:
            m3u_link = None

        if not m3u_link:
            raise ValueError("Video URL not found in response")

        # disk.yandex için referer boş olmalı
        final_referer = "" if "disk.yandex" in m3u_link else ext_ref

        # Recursive extraction check
        try:
            from KekikStream.Core.Extractor.ExtractorManager import ExtractorManager
            # Import inside method to avoid circular dependency
            manager = ExtractorManager()
            if nested_extractor := manager.find_extractor(m3u_link):
                # Use recursive extraction
                return await nested_extractor.extract(m3u_link, referer=final_referer)
        except Exception:
            # If recursion fails, fallback to standard result
            pass

        return ExtractResult(
            name      = self.name,
            url       = m3u_link,
            referer   = final_referer,
            headers   = {},
            subtitles = []
        )
