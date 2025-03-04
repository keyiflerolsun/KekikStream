# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import ExtractorBase, ExtractResult, Subtitle
import re

class ContentX(ExtractorBase):
    name     = "ContentX"
    main_url = "https://contentx.me"

    async def extract(self, url, referer=None) -> list[ExtractResult]:
        if referer:
            self.httpx.headers.update({"Referer": referer})

        istek = await self.httpx.get(url)
        istek.raise_for_status()
        i_source = istek.text

        i_extract = re.search(r"window\.openPlayer\('([^']+)'", i_source)
        if not i_extract:
            raise ValueError("i_extract is null")
        i_extract_value = i_extract[1]

        subtitles = []
        sub_urls  = set()
        for match in re.finditer(r'"file":"([^"]+)","label":"([^"]+)"', i_source):
            sub_url, sub_lang = match.groups()

            if sub_url in sub_urls:
                continue

            sub_urls.add(sub_url)
            subtitles.append(
                Subtitle(
                    name = sub_lang.replace("\\u0131", "ı")
                                 .replace("\\u0130", "İ")
                                 .replace("\\u00fc", "ü")
                                 .replace("\\u00e7", "ç"),
                    url  = self.fix_url(sub_url.replace("\\", ""))
                )
            )

        vid_source_request = await self.httpx.get(f"{self.main_url}/source2.php?v={i_extract_value}", headers={"Referer": referer or self.main_url})
        vid_source_request.raise_for_status()

        vid_source  = vid_source_request.text
        vid_extract = re.search(r'file":"([^"]+)"', vid_source)
        if not vid_extract:
            raise ValueError("vidExtract is null")

        m3u_link = vid_extract[1].replace("\\", "")
        results  = [
            ExtractResult(
                name      = self.name,
                url       = m3u_link,
                referer   = url,
                headers   = {},
                subtitles = subtitles
            )
        ]

        if i_dublaj := re.search(r',\"([^"]+)\",\"Türkçe"', i_source):
            dublaj_value          = i_dublaj[1]
            dublaj_source_request = await self.httpx.get(f"{self.main_url}/source2.php?v={dublaj_value}", headers={"Referer": referer or self.main_url})
            dublaj_source_request.raise_for_status()

            dublaj_source  = dublaj_source_request.text
            dublaj_extract = re.search(r'file":"([^"]+)"', dublaj_source)
            if not dublaj_extract:
                raise ValueError("dublajExtract is null")

            dublaj_link = dublaj_extract[1].replace("\\", "")
            results.append(
                ExtractResult(
                    name      = f"{self.name} Türkçe Dublaj",
                    url       = dublaj_link,
                    referer   = url,
                    headers   = {},
                    subtitles = []
                )
            )

        return results[0] if len(results) == 1 else results