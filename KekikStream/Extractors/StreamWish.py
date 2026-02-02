# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper
from Kekik.Sifreleme  import Packer
from contextlib       import suppress

class StreamWish(ExtractorBase):
    name     = "StreamWish"
    main_url = "https://streamwish.to"

    supported_domains = [
        "streamwish.to", "streamwish.site", "streamwish.xyz", "streamwish.com",
        "embedwish.com", "mwish.pro", "dwish.pro", "wishembed.pro", "wishembed.com",
        "kswplayer.info", "wishfast.top", "sfastwish.com", "strwish.xyz", "strwish.com",
        "flaswish.com", "awish.pro", "obeywish.com", "jodwish.com", "swhoi.com",
        "multimovies.cloud", "uqloads.xyz", "doodporn.xyz", "cdnwish.com", "asnwish.com",
        "nekowish.my.id", "neko-stream.click", "swdyu.com", "wishonly.site", "playerwish.com",
        "streamhls.to", "hlswish.com"
    ]

    def can_handle_url(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)

    def resolve_embed_url(self, url: str) -> str:
        # Kotlin: /f/ -> /, /e/ -> /
        if "/f/" in url:
            return url.replace("/f/", "/")
        if "/e/" in url:
            return url.replace("/e/", "/")
        return url

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        base_url  = self.get_base_url(url)
        embed_url = self.resolve_embed_url(url)
        istek = await self.httpx.get(
            url     = embed_url,
            headers = {
                "Accept"     : "*/*",
                "Connection" : "keep-alive",
                "Referer"    : f"{base_url}/",
                "Origin"     : f"{base_url}/",
                "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            follow_redirects=True
        )
        text = istek.text

        unpacked = ""
        # Eval script bul
        if eval_match := HTMLHelper(text).regex_first(r'(eval\s*\(\s*function[\s\S]+?)<\/script>'):
            with suppress(Exception):
                unpacked = Packer.unpack(eval_match)

        content = unpacked or text
        sel = HTMLHelper(content)

        # Regex: file:\s*"(.*?m3u8.*?)"
        m3u8_url = sel.regex_first(r'file:\s*["\']([^"\']+\.m3u8[^"\']*)["\']')

        if not m3u8_url:
            # Fallback to sources: Kotlin mantığı
            m3u8_url = sel.regex_first(r'sources:\s*\[\s*{\s*file:\s*["\']([^"\']+)["\']')

        if not m3u8_url:
            # p,a,c,k,e,d içinde olabilir
            m3u8_url = sel.regex_first(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']')

        if not m3u8_url:
            # t.r.u.e pattern fallback
            m3u8_url = sel.regex_first(r'file\s*:\s*["\']([^"\']+)["\']')

        if not m3u8_url:
            raise ValueError(f"StreamWish: m3u8 bulunamadı. {url}")

        return ExtractResult(
            name       = self.name,
            url        = self.fix_url(m3u8_url),
            referer    = f"{base_url}/",
            user_agent = self.httpx.headers.get("User-Agent", "")
        )
