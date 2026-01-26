# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle, HTMLHelper

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

    def can_handle_url(self, url: str) -> bool:
        return any(domain in url for domain in self.supported_domains)

    async def extract(self, url: str, referer: str = None) -> list[ExtractResult] | ExtractResult:
        ref = referer or self.get_base_url(url)
        self.httpx.headers.update({"Referer": ref})

        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)

        v_id = sel.regex_first(r"window\.openPlayer\('([^']+)'")
        if not v_id:
            raise ValueError(f"ContentX: ID bulunamadı. {url}")

        subtitles = []
        for s_url, s_lang in sel.regex_all(r'"file":"([^\"]+)","label":"([^\"]+)"'):
            decoded_lang = s_lang.encode().decode('unicode_escape')
            subtitles.append(Subtitle(name=decoded_lang, url=self.fix_url(s_url.replace("\\", ""))))

        results = []
        # Base m3u8
        vid_resp = await self.httpx.get(f"{self.get_base_url(url)}/source2.php?v={v_id}", headers={"Referer": url})
        if m3u8_link := HTMLHelper(vid_resp.text).regex_first(r'file":"([^\"]+)"'):
            m3u8_link = m3u8_link.replace("\\", "").replace("/m.php", "/master.m3u8")
            results.append(ExtractResult(name=self.name, url=m3u8_link, referer=url, subtitles=subtitles))

        # Dublaj Kontrolü
        if dub_id := sel.regex_first(r'["\']([^"\']+)["\'],["\']Türkçe["\']'):
            dub_resp = await self.httpx.get(f"{self.get_base_url(url)}/source2.php?v={dub_id}", headers={"Referer": url})
            if dub_link := HTMLHelper(dub_resp.text).regex_first(r'file":"([^\"]+)"'):
                results.append(ExtractResult(name=f"{self.name} Türkçe Dublaj", url=dub_link.replace("\\", ""), referer=url))

        if not results:
            raise ValueError(f"ContentX: Video linki bulunamadı. {url}")

        return results[0] if len(results) == 1 else results