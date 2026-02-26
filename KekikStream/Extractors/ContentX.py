# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper
import re

class ContentX(ExtractorBase):
    name     = "ContentX"
    main_url = "https://contentx.me"

    # Birden fazla domain destekle
    supported_domains = [
        "contentx.me", "four.contentx.me",
        "dplayer82.site", "sn.dplayer82.site", "four.dplayer82.site", "org.dplayer82.site",
        "dplayer74.site", "sn.dplayer74.site",
        "hotlinger.com", "sn.hotlinger.com",
        "playru.net", "four.playru.net",
        "pichive.online", "four.pichive.online", "pichive.me", "four.pichive.me"
    ]

    @staticmethod
    def _normalize_link(link: str) -> str:
        return link.replace("\\", "").replace("/m.php", "/master.m3u8")

    async def _fetch_source_file(self, base_url: str, content_url: str, vid: str) -> str | None:
        """source2/source endpoint varyasyonlarını dener."""
        for endpoint in ("source2.php", "source.php"):
            resp = await self.httpx.get(f"{base_url}/{endpoint}?v={vid}", headers={"Referer": content_url})
            if file_link := HTMLHelper(resp.text).regex_first(r'file":"([^\"]+)"'):
                return self._normalize_link(file_link)
        return None

    async def extract(self, url: str, referer: str = None) -> list[ExtractResult] | ExtractResult:
        ref = referer or self.get_base_url(url)
        self.httpx.headers.update({"Referer": ref})

        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)

        # Farklı player çağrılarını yakala
        v_id = (
            sel.regex_first(r"window\.openPlayer\(['\"]([^'\"]+)['\"]") or
            sel.regex_first(r"openPlayer\((?:['\"])?([a-zA-Z0-9_-]{6,})(?:['\"])?\)") or
            sel.regex_first(r"[?&]v=([a-zA-Z0-9_-]+)")
        )

        if not v_id:
            # URL'den v parametresini çekmeyi dene
            v_match = re.search(r"[?&]v=([^&]+)", url)
            v_id    = v_match.group(1) if v_match else None

        if not v_id:
            raise ValueError(f"ContentX: ID bulunamadı. {url}")

        subtitles = []
        # Hem çift hem tek tırnak varyasyonları
        sub_matches = sel.regex_all(r'["\']file["\']\s*:\s*["\']([^"\']+)["\']\s*,\s*["\']label["\']\s*:\s*["\']([^"\']+)["\']')
        for s_url, s_lang in sub_matches:
            decoded_lang = s_lang.encode().decode('unicode_escape')
            subtitles.append(Subtitle(name=decoded_lang, url=self.fix_url(self._normalize_link(s_url))))

        results  = []
        base_url = self.get_base_url(url)

        # Base m3u8
        if m3u8_link := await self._fetch_source_file(base_url, url, v_id):
            results.append(ExtractResult(name=self.name, url=self.fix_url(m3u8_link), referer=url, subtitles=subtitles))

        # Dublaj Kontrolü
        dub_id = (
            sel.regex_first(r'["\']([^"\']+)["\']\s*,\s*["\']Türkçe["\']') or
            sel.regex_first(r'["\']dub["\']\s*:\s*["\']([^"\']+)["\']')
        )
        if dub_id:
            if dub_link := await self._fetch_source_file(base_url, url, dub_id):
                results.append(ExtractResult(name=f"{self.name} Türkçe Dublaj", url=self.fix_url(dub_link), referer=url))

        if not results:
            raise ValueError(f"ContentX: Video linki bulunamadı. {url}")

        return results[0] if len(results) == 1 else results
