# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PackedJSExtractor, ExtractResult, HTMLHelper
import contextlib, json

class Ashdi(PackedJSExtractor):
    name     = "Ashdi"
    main_url = "https://ashdi.vip"

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        # Referer trailing slash fix
        ref = referer or "https://uakino.best"
        if ref.endswith("/") and len(ref) > 10:
            ref = ref.rstrip("/")

        resp = await self.httpx.get(
            url     = url,
            headers = {
                "Referer"    : ref,
                "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            }
        )
        secici = HTMLHelper(resp.text)

        # 1. Packed JS veya Direkt HTML içinde ara
        m3u_link = self.unpack_and_find(resp.text)

        if not m3u_link:
            # PlayerJS variant: file:"[720p]https://..." or "file":"https://..."
            m3u_link = secici.regex_first(r'["\']file["\']\s*:\s*["\']([^"\']+)["\']')
            if m3u_link and "]" in m3u_link:
                m3u_link = m3u_link.split("]")[-1]

        if not m3u_link:
            # Another pattern: sources: [{file: "..."}]
            m3u_link = secici.regex_first(r'["\']?sources["\']?\s*:\s*\[\s*\{\s*["\']?file["\']?\s*:\s*["\']([^"\']+)["\']')

        if not m3u_link:
            # Check for direct m3u8 in scripts
            m3u_link = secici.regex_first(r'["\']?(?:file|url|src)["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']')

        if not m3u_link:
            # Check for data-config or similar JSON blobs
            config = secici.regex_first(r'data-config=["\'](\{.*?\})["\']')
            if config:
                with contextlib.suppress(Exception):
                    conf_data = json.loads(config.replace("&quot;", '"'))
                    m3u_link  = conf_data.get("file") or conf_data.get("url")

        if not m3u_link:
            # Check for direct <source> tags if PlayerJS fails
            m3u_link = secici.select_attr("source", "src") or secici.select_attr("video", "src")

        if not m3u_link:
            raise ValueError(f"Ashdi: Video URL bulunamadı. {url}")

        # If it's a relative link (unlikely but possible)
        if m3u_link.startswith("/"):
            m3u_link = f"{self.main_url}{m3u_link}"

        return ExtractResult(
            name       = self.name,
            url        = m3u_link,
            referer    = f"{self.main_url}/",
            user_agent = self.httpx.headers.get("User-Agent")
        )
