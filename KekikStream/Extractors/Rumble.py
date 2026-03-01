# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult
import re

class Rumble(ExtractorBase):
    name     = "Rumble"
    main_url = "https://rumble.com"

    def can_handle_url(self, url: str) -> bool:
        return "rumble.com/embed/" in url

    async def extract(self, url: str, referer: str | None = None) -> ExtractResult | list[ExtractResult]:
        # Embed ID'sini al
        # Ör: https://rumble.com/embed/v749e4a/#?secret=rVdXn6RICm
        match = re.search(r"embed/([^/?#]+)", url)
        if not match:
            raise ValueError(f"{self.name}: Video ID bulunamadı. {url}")

        v_id    = match.group(1)

        # Rumble JSON API
        api_url = f"https://rumble.com/embedJS/u3/?request=video&ver=2&v={v_id}"

        resp = await self.httpx.get(api_url, headers={"Referer": referer or url})
        data = resp.json()

        sources = data.get("u", {})
        if not sources:
            raise ValueError(f"{self.name}: Video kaynakları bulunamadı.")

        # 'tar' anahtarı genellikle HLS/M3U8 bağlantısını içerir
        # Diğer anahtarlar (örn: "480", "720") mp4 bağlantılarını içerir

        results = []
        for res, info in sources.items():
            if res in ["timeline", "audio", "vtt"]:
                continue

            link = info.get("url")
            if not link:
                continue

            if res == "tar":
                label = "HLS"
            elif res == "hls":
                label = "HLS (Alt)"
            elif res == "hlsp":
                label = "VOD"
            elif res.isdigit():
                label = f"{res}p"
            else:
                label = res.upper()

            results.append(ExtractResult(
                name    = f"{self.name} | {label}",
                url     = link,
                referer = url
            ))

        if not results:
            raise ValueError(f"{self.name}: Oynatılabilir bağlantı bulunamadı.")

        # URL bazlı tekilleştirme
        unique_results = []
        seen_urls      = set()

        # Öncelik sırası: HLS > MP4 > Diğer
        def sort_key(x):
            if "HLS" in x.name:
                return 0
            if "MP4" in x.name or "p" in x.name:
                return 1
            return 2

        results.sort(key=sort_key)

        for res in results:
            if res.url not in seen_urls:
                unique_results.append(res)
                seen_urls.add(res.url)

        return unique_results if len(unique_results) > 1 else unique_results[0]
