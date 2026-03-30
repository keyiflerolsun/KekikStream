# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core                            import PackedJSExtractor, ExtractResult, HTMLHelper, M3U8_FILE_REGEX
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import base64, json, re


class Filemoon(PackedJSExtractor):
    name        = "Filemoon"
    main_url    = "https://filemoon.to"
    url_pattern = M3U8_FILE_REGEX

    # Filemoon'un farklı domainlerini destekle
    supported_domains = ["filemoon.to", "filemoon.in", "filemoon.sx", "filemoon.nl", "filemoon.com", "bysedikamoum.com"]

    _UA = "Mozilla/5.0 (X11; Linux x86_64; rv:137.0) Gecko/20100101 Firefox/137.0"

    @staticmethod
    def _b64url_decode(value: str) -> bytes:
        normalized = value.replace("-", "+").replace("_", "/")
        normalized += "=" * ((4 - len(normalized) % 4) % 4)
        return base64.b64decode(normalized)

    @staticmethod
    def _media_id_from_url(url: str) -> str:
        match = re.search(r"/(?:e|d|v|f|download)/([0-9a-zA-Z]+)", url)
        if match:
            return match.group(1)
        return url.rstrip("/").split("/")[-1].split("?", 1)[0]

    @staticmethod
    def _playback_error_message(url: str, response, data: dict | None) -> str | None:
        host = url.split("://", 1)[1].split("/", 1)[0]

        if isinstance(data, dict):
            if error_message := data.get("error"):
                lowered = error_message.lower()
                if "embedding from" in lowered and "not allowed" in lowered:
                    return f"Filemoon: Gömme alanı engelli, {host} bu videoyu oynatmaya izin vermiyor. {url}"
                return f"Filemoon: Playback API hatası - {error_message}. {url}"

        location = (response.headers.get("location") or "").lower() if response else ""
        if "ww16.filemoon.nl" in location:
            return f"Filemoon: filemoon.nl playback alanı park yönlendirmesine düştü. {url}"

        content_type  = (response.headers.get("content-type") or "").lower() if response else ""
        response_text = response.text.lower() if response and "html" in content_type else ""
        if host == "filemoon.nl" and "redirect_link" in response_text and "ww16.filemoon.nl" in response_text:
            return f"Filemoon: filemoon.nl playback alanı park yönlendirmesine düştü. {url}"

        return None

    @classmethod
    def _decrypt_playback_sources(cls, playback: dict) -> list[dict] | None:
        if not playback:
            return None

        payload   = playback.get("payload")
        iv        = playback.get("iv")
        key_parts = playback.get("key_parts") or []
        if not payload or not iv or not key_parts:
            return None

        try:
            key       = b"".join(cls._b64url_decode(part) for part in key_parts)
            decrypted = AESGCM(key).decrypt(cls._b64url_decode(iv), cls._b64url_decode(payload), None)
            data      = json.loads(decrypted.decode("latin1"))
            if isinstance(data, dict):
                return data.get("sources")
        except Exception:
            return None

        return None

    async def _fetch_playback_sources(self, url: str) -> tuple[list[dict] | None, str, str | None]:
        host         = url.split("://", 1)[1].split("/", 1)[0]
        root_referer = f"https://{host}/"
        media_id     = self._media_id_from_url(url)
        api_url      = f"https://{host}/api/videos/{media_id}/embed/playback"
        headers      = {
            "User-Agent"       : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Referer"          : root_referer,
            "Origin"           : root_referer.rstrip("/"),
            "X-Requested-With" : "XMLHttpRequest",
        }

        try:
            response = await self.httpx.get(api_url, headers=headers)
            data     = response.json() if "json" in (response.headers.get("content-type") or "").lower() else None
        except Exception:
            try:
                response = await self.async_cf_get(api_url, headers=headers)
                data     = response.json() if "json" in (response.headers.get("content-type") or "").lower() else None
            except Exception:
                return None, root_referer, None

        if not isinstance(data, dict):
            return None, root_referer, self._playback_error_message(api_url, response, data)

        sources = data.get("sources")
        if sources:
            return sources, root_referer, None

        decrypted_sources = self._decrypt_playback_sources(data.get("playback"))
        if decrypted_sources:
            return decrypted_sources, root_referer, None

        return None, root_referer, self._playback_error_message(api_url, response, data)

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        if "/download/" in url:
            url = url.replace("/download/", "/e/")

        playback_sources, playback_referer, playback_error = await self._fetch_playback_sources(url)
        if playback_sources:
            for source in playback_sources:
                source_url = source.get("url")
                if source_url:
                    return ExtractResult(
                        name       = source.get("label") or self.name,
                        url        = self.fix_url(source_url),
                        referer    = playback_referer,
                        user_agent = self._UA,
                    )

        headers = {
            "Referer"        : url,
            "Sec-Fetch-Dest" : "iframe",
            "Sec-Fetch-Mode" : "navigate",
            "Sec-Fetch-Site" : "cross-site",
            "User-Agent"     : self._UA,
        }
        self.httpx.headers.update(headers)

        try:
            istek = await self.httpx.get(url)
            if len(istek.text) < 5000:
                raise Exception("CF challenge suspected")
        except Exception:
            istek  = await self.async_cf_get(url, headers=headers)
        secici = HTMLHelper(istek.text)

        # iframe varsa takip et
        if iframe_src := secici.select_attr("iframe", "src"):
            url = self.fix_url(iframe_src)
            try:
                istek = await self.httpx.get(url)
                if len(istek.text) < 5000:
                    raise Exception("CF challenge suspected")
            except Exception:
                istek  = await self.async_cf_get(url, headers=headers)
            secici = HTMLHelper(istek.text)

        m3u8_url = self.unpack_and_find(istek.text)

        if not m3u8_url:
            # Fallback: m3u8 or mp4 check
            m3u8_url = secici.regex_first(r'file\s*:\s*["\']([^"\']+\.(?:m3u8|mp4)[^"\']*)["\']')

        if not m3u8_url and playback_error:
            raise ValueError(playback_error)

        if not m3u8_url:
            raise ValueError(f"Filemoon: Video URL bulunamadı. {url}")

        return ExtractResult(
            name       = self.name,
            url        = self.fix_url(m3u8_url),
            referer    = f"{self.get_base_url(url)}/",
            user_agent = self._UA,
        )
