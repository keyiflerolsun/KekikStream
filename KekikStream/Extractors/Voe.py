# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper
from urllib.parse     import urlparse
import base64, json, re


class Voe(ExtractorBase):
    name     = "Voe"
    main_url = "https://voe.sx"

    supported_domains = [
        "voe.sx",
        "yip.su",
        "metagnathtuggers.com",
        "graceaddresscommunity.com",
        "sethniceletter.com",
        "maxfinishseveral.com",
        "lauradaydo.com",
        "dianaavoidthey.com",
        "lancewhosedifficult.com",
        "donaldlineelse.com",
        "tubelessceliolymph.com",
        "simpulumlamerop.com",
        "urochsunloath.com",
        "nathanfromsubject.com",
    ]

    denied_markers = [
        "File access denied",
        "Dosya erişimi reddedildi",
        "Bu dosyanın sahibi ülkenize erişimi kısıtlamıştır",
    ]

    @staticmethod
    def _decode_base64_json(raw: str) -> str | None:
        """VOE bazen urlsafe/paddingsiz base64 döndürüyor."""
        if not raw:
            return None

        raw = raw.strip().strip("\"'")
        # base64 padding düzelt
        pad = len(raw) % 4
        if pad:
            raw += "=" * (4 - pad)

        for decoder in (base64.b64decode, base64.urlsafe_b64decode):
            try:
                return decoder(raw).decode("utf-8", errors="ignore")
            except Exception:
                continue

        return None

    @staticmethod
    def _rot13(text: str) -> str:
        result = []
        for char in text:
            if "a" <= char <= "z":
                result.append(chr((ord(char) - ord("a") + 13) % 26 + ord("a")))
            elif "A" <= char <= "Z":
                result.append(chr((ord(char) - ord("A") + 13) % 26 + ord("A")))
            else:
                result.append(char)
        return "".join(result)

    @staticmethod
    def _char_shift(text: str, shift: int) -> str:
        return "".join(chr(ord(char) - shift) for char in text)

    @classmethod
    def _decrypt_f7(cls, encoded: str) -> dict | None:
        if not encoded:
            return None

        try:
            value = cls._rot13(encoded.strip())
            for pattern in ("@$", "^^", "~@", "%?", "*~", "!!", "#&"):
                value = value.replace(pattern, "_")
            value = value.replace("_", "")

            first = cls._decode_base64_json(value)
            if not first:
                return None

            shifted = cls._char_shift(first, 3)
            second  = cls._decode_base64_json(shifted[::-1])
            if not second:
                return None

            data = json.loads(second)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    @staticmethod
    def _extract_application_json(content: str) -> str | None:
        match = re.search(
            r'<script[^>]+type=["\']application/json["\'][^>]*>\s*\["(.+?)"\]\s*</script>',
            content,
            re.DOTALL,
        )
        if not match:
            return None

        return match.group(1).replace('\\"', '"')

    @staticmethod
    def _normalize_url(url: str) -> str:
        parsed = urlparse(url)
        host   = parsed.netloc or "voe.sx"
        path   = parsed.path.rstrip("/")

        if "/download/" in path:
            path = path.replace("/download/", "/e/")
        elif path.endswith("/download"):
            video_id = path.rsplit("/download", 1)[0].split("/")[-1]
            path     = f"/e/{video_id}"
        elif "/e/" not in path:
            video_id = path.split("/")[-1]
            path     = f"/e/{video_id}"

        if not host:
            host = "voe.sx"

        return f"https://{host}{path}"

    async def _fetch_page(self, url: str, referer: str | None) -> str:
        headers = {"Referer": referer or self.main_url}
        try:
            resp = await self.async_cf_get(url, headers=headers)
        except Exception:
            resp = await self.httpx.get(url, headers=headers)
        return resp.text

    @classmethod
    def _detect_denied_reason(cls, content: str) -> str | None:
        lowered = content.lower()
        for marker in cls.denied_markers:
            if marker.lower() in lowered:
                return marker
        return None

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        url     = self._normalize_url(url)
        content = await self._fetch_page(url, referer)
        secici  = HTMLHelper(content)

        for _ in range(2):
            js_redirect = secici.regex_first(r"window\.location\.(?:href|replace)\s*(?:=|\()\s*['\"](https?://[^'\"]+)['\"]")
            if not js_redirect:
                break
            content = await self._fetch_page(js_redirect, url)
            secici  = HTMLHelper(content)

        denied_reason = self._detect_denied_reason(content)
        if denied_reason:
            raise ValueError(f"Voe: Bölgesel/erişim engeli tespit edildi. {url}")

        encoded_json = self._extract_application_json(content)
        if encoded_json:
            payload = self._decrypt_f7(encoded_json)
            if payload:
                video_url = payload.get("source") or payload.get("direct_access_url") or payload.get("file") or payload.get("hls")
                if video_url:
                    return ExtractResult(name=self.name, url=video_url.replace("\\/", "/").replace("&amp;", "&"), referer=url)

        # Method 1: wc0 base64 encoded JSON
        script_val = secici.regex_first(r"(?:var|let|const)?\s*wc0\s*=\s*['\"]([^'\"]+)['\"]")
        if not script_val:
            script_val = secici.regex_first(r"atob\(['\"]([^'\"]+)['\"]\)")

        if script_val:
            try:
                decoded = self._decode_base64_json(script_val)
                if decoded:
                    js_data   = json.loads(decoded)
                    video_url = js_data.get("file") or js_data.get("hls")
                    if video_url:
                        return ExtractResult(name=self.name, url=video_url.replace("\\/", "/"), referer=url)
            except Exception:
                pass

        # Method 2: sources/file/hls regex
        video_url = secici.regex_first(r"sources\s*:\s*\[\s*\{\s*(?:src|file)\s*:\s*['\"]([^'\"]+)['\"]")
        if not video_url:
            video_url = secici.regex_first(r"['\"]?file['\"]?\s*:\s*['\"]([^'\"]+\.(?:m3u8|mp4)[^'\"]*)['\"]")

        if not video_url:
            video_url = secici.regex_first(r"hls\s*:\s*['\"]([^'\"]+)['\"]")

        if not video_url:
            raise ValueError(f"Voe: Video URL bulunamadı. {url}")

        return ExtractResult(name=self.name, url=video_url.replace("\\/", "/").replace("&amp;", "&"), referer=url)
