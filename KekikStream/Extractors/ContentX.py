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

    async def extract(self, url, referer=None) -> list[ExtractResult]:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        # Dinamik base URL kullan
        base_url = self.get_base_url(url)

        istek = await self.httpx.get(url)
        istek.raise_for_status()
        i_source = istek.text

        i_extract_value = HTMLHelper(i_source).regex_first(r"window\.openPlayer\('([^']+)'")
        if not i_extract_value:
            raise ValueError("i_extract is null")

        subtitles = []
        sub_urls  = set()
        for sub_url, sub_lang in HTMLHelper(i_source).regex_all(r'"file":"([^\"]+)","label":"([^\"]+)"'):

            if sub_url in sub_urls:
                continue

            sub_urls.add(sub_url)
            subtitles.append(
                Subtitle(
                    name = sub_lang.replace("\\u0131", "ı")
                                 .replace("\\u0130", "İ")
                                 .replace("\\u00fc", "ü")
                                 .replace("\\u00e7", "ç")
                                 .replace("\\u011f", "ğ")
                                 .replace("\\u015f", "ş")
                                 .replace("\\u011e", "Ğ")
                                 .replace("\\u015e", "Ş"),
                    url  = self.fix_url(sub_url.replace("\\/", "/").replace("\\", ""))
                )
            )

        # base_url kullan (contentx.me yerine)
        vid_source_request = await self.httpx.get(f"{base_url}/source2.php?v={i_extract_value}", headers={"Referer": referer or base_url})
        vid_source_request.raise_for_status()

        vid_source  = vid_source_request.text
        m3u_link = HTMLHelper(vid_source).regex_first(r'file":"([^\"]+)"')
        if not m3u_link:
            raise ValueError("vidExtract is null")

        m3u_link = m3u_link.replace("\\", "").replace("/m.php", "/master.m3u8")
        results  = [
            ExtractResult(
                name      = self.name,
                url       = m3u_link,
                referer   = url,
                subtitles = subtitles
            )
        ]

        dublaj_value = HTMLHelper(i_source).regex_first(r'["\']([^"\']+)["\'],["\']Türkçe["\']')
        if dublaj_value:
            try:
                dublaj_source_request = await self.httpx.get(f"{base_url}/source2.php?v={dublaj_value}", headers={"Referer": referer or base_url})
                dublaj_source_request.raise_for_status()

                dublaj_source  = dublaj_source_request.text
                dublaj_link = HTMLHelper(dublaj_source).regex_first(r'file":"([^\"]+)"')
                if dublaj_link:
                    dublaj_link = dublaj_link.replace("\\", "")
                    results.append(
                        ExtractResult(
                            name      = f"{self.name} Türkçe Dublaj",
                            url       = dublaj_link,
                            referer   = url,
                            subtitles = []
                        )
                    )
            except Exception:
                pass

        return results[0] if len(results) == 1 else results