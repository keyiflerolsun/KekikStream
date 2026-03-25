# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, HTMLHelper
import base64
import json


class Voe(ExtractorBase):
    name     = "Voe"
    main_url = "https://voe.sx"

    supported_domains = ["voe.sx", "yip.su", "metagnathtuggers.com", "graceaddresscommunity.com", "sethniceletter.com", "maxfinishseveral.com", "lauradaydo.com"]

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

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        if "/download/" in url:
            url = url.replace("/download/", "/e/")
        elif "/e/" not in url and "voe.sx" in url:
            # v -> e conversion if needed
            v_id = url.split("/")[-1]
            url  = f"https://voe.sx/e/{v_id}"

        try:
            # Voe often uses protection (DDG, etc.), use cloudscraper async wrapper
            resp    = await self.async_cf_get(url, headers={"Referer": referer or self.main_url})
            content = resp.text
        except Exception:
            resp    = await self.httpx.get(url, headers={"Referer": referer or self.main_url})
            content = resp.text

        secici = HTMLHelper(content)

        # JS redirect takibi
        js_redirect = secici.regex_first(r"window\.location\.(?:href|replace)\s*(?:=|\()\s*['\"](https?://[^'\"]+)['\"]")
        if js_redirect and "Redirecting" in content:
            try:
                resp    = await self.async_cf_get(js_redirect, headers={"Referer": url})
                content = resp.text
            except Exception:
                resp    = await self.httpx.get(js_redirect, headers={"Referer": url})
                content = resp.text
            secici  = HTMLHelper(content)

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
