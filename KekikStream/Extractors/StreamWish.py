# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PackedJSExtractor, ExtractResult, HTMLHelper, M3U8_FILE_REGEX
from urllib.parse     import urljoin, urlparse


class StreamWish(PackedJSExtractor):
    name        = "StreamWish"
    main_url    = "https://streamwish.to"
    url_pattern = M3U8_FILE_REGEX

    supported_domains = [
        "streamwish.to",
        "streamwish.site",
        "streamwish.xyz",
        "streamwish.com",
        "streamplay.to",
        "stre4mpay.one",
        "listeamed.net",
        "ts.getducked.xyz",
        "getducked.xyz",
        "embedwish.com",
        "mwish.pro",
        "dwish.pro",
        "wishembed.pro",
        "wishembed.com",
        "kswplayer.info",
        "wishfast.top",
        "sfastwish.com",
        "strwish.xyz",
        "strwish.com",
        "flaswish.com",
        "awish.pro",
        "obeywish.com",
        "jodwish.com",
        "swhoi.com",
        "multimovies.cloud",
        "uqloads.xyz",
        "doodporn.xyz",
        "cdnwish.com",
        "asnwish.com",
        "nekowish.my.id",
        "neko-stream.click",
        "swdyu.com",
        "wishonly.site",
        "playerwish.com",
        "streamhls.to",
        "hlswish.com",
        "kitraskimisi.com",
        "engifuosi.com",
        "hglink.to",
        "ghbrisk.com",
        "doramasfoxito.p2pplay.online",
        "p2pplay.pro",
        "doramaslatinox.p2pplay.pro",
        "p2pplay.online",
        "doramafox.p2pplay.online",
        "sbfast.com",
        "vtube.to",
        "vudeo.io",
        "vadshar.com",
    ]

    _DIRECT_ALIAS_MAP = {
        "hglink.to": "ghbrisk.com",
    }

    def _normalize_alias_url(self, url: str) -> str:
        parsed = urlparse(url)
        host   = (parsed.netloc or "").lower()

        if host in self._DIRECT_ALIAS_MAP:
            return parsed._replace(netloc=self._DIRECT_ALIAS_MAP[host]).geturl()

        return url

    def resolve_embed_url(self, url: str) -> str:
        url = self._normalize_alias_url(url)

        # Handle hash based URLs like doramasfoxito.p2pplay.online/#ID
        if "#" in url and not any(x in url for x in ["/e/", "/f/", "/d/", "/download/"]):
            parts = url.split("#")
            if len(parts[-1]) > 5:
                return f"{parts[0].rstrip('/')}/e/{parts[-1]}"

        # StreamWish sites usually prefer /e/ for embedding
        if "/download/" in url:
            return url.replace("/download/", "/e/")
        if "/f/" in url:
            return url.replace("/f/", "/e/")
        if "/d/" in url:
            return url.replace("/d/", "/e/")

        # If it doesn't have /e/ already, add it
        if "/e/" not in url:
            parsed = urlparse(url)
            code   = parsed.path.rstrip("/").split("/")[-1]
            if code and "." not in code: # basic check for code vs file
                return f"{parsed.scheme}://{parsed.netloc}/e/{code}"

        return url

    def _extract_direct_media(self, html: str) -> str | None:
        media_url = self.unpack_and_find(html)
        if media_url:
            return media_url

        helper    = HTMLHelper(html)
        media_url = (
            helper.regex_first(r'file\s*:\s*["\']([^"\']+)["\']')
            or helper.regex_first(r'sources\s*:\s*\[\s*\{\s*file\s*:\s*["\']([^"\']+)["\']')
            or helper.regex_first(r'["\'](https?://[^"\']+\.(?:m3u8|mp4)[^"\']*)["\']')
        )

        if not media_url:
            return None

        if any(marker in media_url for marker in (".m3u8", ".mp4", "/hls/", "master.txt", "/manifests/")):
            return media_url

        return None

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        embed_url = self.resolve_embed_url(url)
        base_url  = self.get_base_url(embed_url)
        headers   = {
            "Accept"     : "*/*",
            "Connection" : "keep-alive",
            "Referer"    : referer or f"{base_url}/",
            "Origin"     : f"{base_url}/",
            "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }

        try:
            istek = await self.httpx.get(url=embed_url, headers=headers, follow_redirects=True)
            html  = istek.text
        except Exception:
            istek = await self.async_cf_get(url=embed_url, headers=headers)
            html  = istek.text

        m3u8_url = self._extract_direct_media(html)
        if not m3u8_url:
            download_urls = []
            if "/d/" in embed_url:
                download_urls.append(embed_url)
            if "/e/" in embed_url:
                download_urls.append(embed_url.replace("/e/", "/d/"))

            seen = set()
            for download_url in download_urls:
                if not download_url or download_url in seen:
                    continue
                seen.add(download_url)

                try:
                    download_resp = await self.httpx.get(url=download_url, headers=headers, follow_redirects=True)
                    download_html = download_resp.text
                except Exception:
                    download_resp = await self.async_cf_get(url=download_url, headers=headers)
                    download_html = download_resp.text

                sel            = HTMLHelper(download_html)
                download_links = sel.select_attrs("a[href*='/f/']", "href")
                if download_links:
                    def quality_rank(link: str) -> int:
                        if link.endswith("_h"):
                            return 0
                        if link.endswith("_n"):
                            return 1
                        if link.endswith("_l"):
                            return 2
                        return 3

                    gate_detected = False
                    for candidate_link in sorted(download_links, key=quality_rank):
                        candidate_url = urljoin(f"{base_url}/", candidate_link)

                        try:
                            candidate_resp = await self.httpx.get(url=candidate_url, headers=headers, follow_redirects=True)
                            candidate_html = candidate_resp.text
                        except Exception:
                            candidate_resp = await self.async_cf_get(url=candidate_url, headers=headers)
                            candidate_html = candidate_resp.text

                        candidate_media = self._extract_direct_media(candidate_html)
                        if candidate_media:
                            return ExtractResult(
                                name       = self.name,
                                url        = self.fix_url(candidate_media),
                                referer    = candidate_url,
                                user_agent = self.httpx.headers.get("User-Agent", ""),
                            )

                        candidate_helper = HTMLHelper(candidate_html)
                        if candidate_helper.select_attr("form input[name='op'][value='download_orig']", "value") or "g-recaptcha" in candidate_html:
                            gate_detected = True

                    if gate_detected:
                        raise ValueError(f"{self.name}: Direct media yerine captcha korumali download sayfasi dondu. {url}")

        if not m3u8_url:
            raise ValueError(f"StreamWish: m3u8 bulunamadı. {url}")

        return ExtractResult(name=self.name, url=self.fix_url(m3u8_url), referer=f"{base_url}/", user_agent=self.httpx.headers.get("User-Agent", ""))
