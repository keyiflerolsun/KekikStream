# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

import json, base64
from urllib.parse     import urlparse
from Crypto.Cipher    import AES
from KekikStream.Core import ExtractorBase, ExtractResult

MIRROR_DOMAINS = [
    "bysezejataos.com",
    "bysebuho.com",
    "bysevepoin.com",
    "byseqekaho.com",
]


class ByseSX(ExtractorBase):
    name     = "ByseSX"
    main_url = "https://byse.sx"

    supported_domains = [
        "byse.sx",
        "bysesukior.com",
        "bysejikuar.com",
        "bysezoxexe.com",
        "bysezejataos.com",
        "bysebuho.com",
        "bysevepoin.com",
        "byseqekaho.com",
        "bysesx.com",
    ]

    @staticmethod
    def _b64url_decode(s: str) -> bytes:
        fixed = s.replace("-", "+").replace("_", "/")
        pad   = (4 - len(fixed) % 4) % 4
        return base64.b64decode(fixed + "=" * pad)

    async def _api_get(self, code: str, host: str, referer: str = None):
        """details API'sini dene; 403 dönerse mirror domain'lere veya referer'a göre Origin değiştir."""
        candidates = [host] + MIRROR_DOMAINS

        # Eğer referer varsa, onun domain'ini de Origin olarak denemek isteyebiliriz
        origin_from_referer = None
        if referer:
            ref_parsed          = urlparse(referer)
            origin_from_referer = f"{ref_parsed.scheme}://{ref_parsed.netloc}"

        for domain in candidates:
            headers = {"Origin": f"https://{domain}", "Referer": f"https://{domain}/e/{code}"}
            resp    = await self.async_cf_get(f"https://{domain}/api/videos/{code}/embed/details", headers=headers, timeout=12)

            if resp.status_code == 200:
                return resp.json()

            # 403 dönerse referer origin'ini dene
            if resp.status_code == 403 and origin_from_referer:
                headers["Origin"] = origin_from_referer
                resp = await self.async_cf_get(f"https://{domain}/api/videos/{code}/embed/details", headers=headers, timeout=12)
                if resp.status_code == 200:
                    return resp.json()

            if resp.status_code == 404:
                raise ValueError(f"ByseSX: Video bulunamadı. {code}")

        raise ValueError(f"ByseSX: API erişimi başarısız (403/Mirror Fail). {code}")

    async def extract(self, url: str, referer: str = None) -> ExtractResult:
        parsed = urlparse(url)
        host   = parsed.netloc.lstrip("www.")

        # /api/get/ pattern support
        if "/api/get/" in url:
            headers = {"Referer": referer or f"https://{host}/"}
            resp    = await self.async_cf_get(url, headers=headers)
            if resp.status_code == 200:
                data    = resp.json()
                sources = data.get("sources") or data.get("data", {}).get("sources", [])
                if sources:
                    best = max(sources, key=lambda s: s.get("bitrate_kbps", 0))
                    return ExtractResult(
                        name    = self.name,
                        url     = best["url"],
                        referer = url,
                    )

        code = parsed.path.rstrip("/").rsplit("/", 1)[-1]

        # 1) details
        details         = await self._api_get(code, host, referer=referer)
        embed_frame_url = details["embed_frame_url"]

        # 2) playback
        fp           = urlparse(embed_frame_url)
        embed_base   = f"{fp.scheme}://{fp.netloc}"
        embed_code   = fp.path.rstrip("/").rsplit("/", 1)[-1]
        playback_url = f"{embed_base}/api/videos/{embed_code}/embed/playback"

        headers  = {
            "accept"         : "*/*",
            "referer"        : embed_frame_url,
            "x-embed-parent" : url,
        }
        resp     = await self.async_cf_get(playback_url, headers=headers, timeout=12)
        playback = resp.json().get("playback")
        if not playback:
            raise ValueError(f"ByseSX: Playback verisi bulunamadı. {url}")

        # 3) AES-256-GCM decrypt
        key_bytes    = self._b64url_decode(playback["key_parts"][0]) + self._b64url_decode(playback["key_parts"][1])
        iv_bytes     = self._b64url_decode(playback["iv"])
        cipher_bytes = self._b64url_decode(playback["payload"])

        tag        = cipher_bytes[-16:]
        ciphertext = cipher_bytes[:-16]

        cipher    = AES.new(key_bytes, AES.MODE_GCM, nonce=iv_bytes)
        plaintext = cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8")

        if plaintext.startswith("\ufeff"):
            plaintext = plaintext[1:]

        data    = json.loads(plaintext)
        sources = data.get("sources", [])
        if not sources:
            raise ValueError(f"ByseSX: Kaynak bulunamadı. {url}")

        best    = max(sources, key=lambda s: s.get("bitrate_kbps", 0))
        ref_url = f"{embed_base}/"

        return ExtractResult(
            name    = self.name,
            url     = best["url"],
            referer = ref_url,
        )
