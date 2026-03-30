# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PackedJSExtractor, ExtractResult, HTMLHelper, M3U8_FILE_REGEX
from urllib.parse     import urlparse, urlunparse
import re


class VidHide(PackedJSExtractor):
    name        = "VidHide"
    main_url    = "https://vidhidepro.com"
    url_pattern = M3U8_FILE_REGEX

    fallback_hosts = [
        "vidhidefast.com",
        "callistanise.com",
    ]

    dead_host_fallbacks = {
        "vidhide.com",
        "vidhidepro.com",
        "vidhidevip.com",
        "vidhidepre.com",
        "filelions.online",
        "filelions.to",
        "smoothpre.com",
        "dhtpre.com",
        "peytonepre.com",
        "movearnpre.com",
        "dintezuvio.com",
        "moorearn.com",
        "travid.pro",
    }

    denied_markers = [
        "Countries are not allowed",
        "Country not allowed",
        "Access denied",
        "Forbidden",
    ]

    timeout_markers = [
        "522: Connection timed out",
        "Connection timed out",
    ]

    # Birden fazla domain destekle
    supported_domains = [
        "vidhidepro.com",
        "vidhide.com",
        "vidhidefast.com",
        "callistanise.com",
        "rubyvidhub.com",
        "vidhidevip.com",
        "vidhideplus.com",
        "vidhidepre.com",
        "movearnpre.com",
        "moorearn.com",
        "travid.pro",
        "vidhidehub.com",
        "dhcplay.com",
        "hglink.to",
        "ryderjet.com",
        "mycloudz.cc",
        "oneupload.to",
        "filelions.live",
        "filelions.online",
        "filelions.to",
        "filelions.top",
        "kinoger.be",
        "smoothpre.com",
        "dhtpre.com",
        "peytonepre.com",
        "minochinos.com",
    ]

    def get_embed_url(self, url: str) -> str:
        if "/d/" in url:
            return url.replace("/d/", "/v/")
        elif "/download/" in url:
            return url.replace("/download/", "/v/")
        elif "/file/" in url:
            return url.replace("/file/", "/v/")
        elif "/embed/" in url:
            return url.replace("/embed/", "/v/")
        else:
            return url.replace("/f/", "/v/")

    @staticmethod
    def _replace_host(url: str, host: str) -> str:
        parsed = urlparse(url)
        return urlunparse((parsed.scheme or "https", host, parsed.path, parsed.params, parsed.query, parsed.fragment))

    def _candidate_urls(self, embed_url: str) -> list[str]:
        parsed     = urlparse(embed_url)
        host       = parsed.netloc
        candidates = [embed_url]

        if host in self.dead_host_fallbacks:
            for fallback_host in self.fallback_hosts:
                fallback_url = self._replace_host(embed_url, fallback_host)
                if fallback_url not in candidates:
                    candidates.append(fallback_url)

        return candidates

    @staticmethod
    def _response_url(response, fallback: str) -> str:
        url = getattr(response, "url", fallback)
        return str(url) if url else fallback

    @classmethod
    def _detect_denied_reason(cls, text: str) -> str | None:
        lowered = text.lower()
        for marker in cls.denied_markers:
            if marker.lower() in lowered:
                return marker
        return None

    @classmethod
    def _is_timeout_page(cls, status_code: int | None, text: str) -> bool:
        if status_code == 522:
            return True

        lowered = text.lower()
        return any(marker.lower() in lowered for marker in cls.timeout_markers)

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        base_url = self.get_base_url(url)
        name     = "EarnVids" if any(x in base_url for x in ["smoothpre.com", "dhtpre.com", "peytonepre.com", "movearnpre.com", "moorearn.com", "travid.pro"]) else self.name

        # Kotlin Headers
        headers = {
            "Sec-Fetch-Dest" : "empty",
            "Sec-Fetch-Mode" : "cors",
            "Sec-Fetch-Site" : "cross-site",
            "Origin"         : f"{base_url}/",
            "Referer"        : referer or f"{base_url}/",
        }

        embed_url      = self.get_embed_url(url)
        istek          = None
        text           = ""
        final_url      = embed_url
        candidate_urls = self._candidate_urls(embed_url)

        for candidate_url in candidate_urls:
            try:
                istek = await self.httpx.get(candidate_url, headers=headers, follow_redirects=True)
                text  = istek.text
            except Exception:
                try:
                    istek = await self.async_cf_get(candidate_url, headers=headers, follow_redirects=True)
                    text  = istek.text
                except Exception:
                    istek = None
                    text  = ""

            if not istek:
                continue

            final_url = self._response_url(istek, candidate_url)
            if not self._is_timeout_page(getattr(istek, "status_code", None), text):
                break

        final_base_url = self.get_base_url(final_url)
        if any(host in final_base_url for host in ["callistanise.com", "movearnpre.com", "smoothpre.com", "dhtpre.com", "peytonepre.com", "moorearn.com", "travid.pro"]):
            name = "EarnVids"

        denied_reason = self._detect_denied_reason(text)
        if denied_reason:
            raise ValueError(f"{name}: Bölgesel/erişim engeli tespit edildi. {final_url}")

        if self._is_timeout_page(getattr(istek, "status_code", None) if istek else None, text):
            raise ValueError(f"{name}: Host erişilemedi (timeout/522). {final_url}")

        # Silinmiş dosya kontrolü
        if any(x in text for x in ["File is no longer available", "File Not Found", "Video silinmiş"]):
            raise ValueError(f"{name}: Video silinmiş. {url}")

        # JS Redirect Kontrolü (OneUpload vb.)
        if js_redirect := HTMLHelper(text).regex_first(r"window\.location\.replace\(['\"]([^'\"]+)['\"]\)") or HTMLHelper(text).regex_first(r"window\.location\.href\s*=\s*['\"]([^'\"]+)['\"]"):
            target_url = js_redirect
            if not target_url.startswith("http"):
                target_url = self.fix_url(target_url)

            istek = await self.httpx.get(target_url, headers={"Referer": embed_url}, follow_redirects=True)
            text  = istek.text

            denied_reason = self._detect_denied_reason(text)
            if denied_reason:
                raise ValueError(f"{name}: Bölgesel/erişim engeli tespit edildi. {self._response_url(istek, target_url)}")

        sel = HTMLHelper(text)

        # Packed JS'den m3u8 çıkarmayı dene (unpack_and_find helper)
        m3u8_url = self.unpack_and_find(text)

        # Çoklu m3u8 sonucu olabilir (regex ile tüm m3u8'leri bul)
        if not m3u8_url:
            m3u8_matches = re.findall(r'(?:file|src|url)["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']', text)
            if not m3u8_matches:
                 # Try finding in scripts without extension check
                 m3u8_matches = re.findall(r'["\'](https?://[^"\']+\.m3u8[^"\']*)["\']', text)
        else:
            m3u8_matches = [m3u8_url]

        results = []
        for m3u8 in m3u8_matches:
            results.append(ExtractResult(name=name, url=self.fix_url(m3u8), referer=f"{final_base_url}/", user_agent=self.httpx.headers.get("User-Agent", "")))

        if not results:
            # Fallback: sources pattern
            if m3u8_url := sel.regex_first(r'sources:\s*\[\s*\{\s*file:\s*"([^"]+)"'):
                results.append(ExtractResult(name=name, url=self.fix_url(m3u8_url), referer=f"{final_base_url}/", user_agent=self.httpx.headers.get("User-Agent", "")))

        if not results:
            raise ValueError(f"{name}: Video URL bulunamadı. {url}")

        return results[0] if len(results) == 1 else results
