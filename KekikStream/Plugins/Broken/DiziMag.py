# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
from Kekik.Sifreleme  import AESManager
import re, json

class DiziMag(PluginBase):
    name        = "DiziMag"
    language    = "tr"
    main_url    = "https://dizimag.lol"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "DiziMag ile yabancı dizi izle ve film izle keyfi! Full HD 1080p kalite, güncel içerikler ve geniş arşivle sinema deneyimini yaşa."

    main_page   = {
        f"{main_url}/dizi/tur/aile"             : "Aile Dizi",
        f"{main_url}/dizi/tur/aksiyon-macera"   : "Aksiyon-Macera Dizi",
        f"{main_url}/dizi/tur/animasyon"        : "Animasyon Dizi",
        f"{main_url}/dizi/tur/bilim-kurgu-fantazi" : "Bilim Kurgu Dizi",
        f"{main_url}/dizi/tur/dram"             : "Dram Dizi",
        f"{main_url}/dizi/tur/gizem"            : "Gizem Dizi",
        f"{main_url}/dizi/tur/komedi"           : "Komedi Dizi",
        f"{main_url}/dizi/tur/suc"              : "Suç Dizi",
        f"{main_url}/film/tur/aksiyon"          : "Aksiyon Film",
        f"{main_url}/film/tur/bilim-kurgu"      : "Bilim-Kurgu Film",
        f"{main_url}/film/tur/dram"             : "Dram Film",
        f"{main_url}/film/tur/fantastik"        : "Fantastik Film",
        f"{main_url}/film/tur/gerilim"          : "Gerilim Film",
        f"{main_url}/film/tur/komedi"           : "Komedi Film",
        f"{main_url}/film/tur/korku"            : "Korku Film",
        f"{main_url}/film/tur/macera"           : "Macera Film",
        f"{main_url}/film/tur/romantik"         : "Romantik Film",
        f"{main_url}/film/tur/suc"              : "Suç Film",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}/{page}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.poster-long"):
            title  = veri.select_text("div.poster-long-subject h2")
            href   = veri.select_attr("div.poster-long-subject a", "href")
            poster = veri.select_attr("div.poster-long-image img", "data-src")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek = await self.httpx.post(
            f"{self.main_url}/search",
            data    = {"query": query},
            headers = {
                "X-Requested-With" : "XMLHttpRequest",
                "Content-Type"     : "application/x-www-form-urlencoded; charset=UTF-8",
            },
        )

        results = []
        try:
            data = istek.json()
            if not data.get("success"):
                return results

            html   = data.get("theme", "")
            secici = HTMLHelper(html)

            for li in secici.select("ul li"):
                href = li.select_attr("a", "href")
                if not href or ("/dizi/" not in href and "/film/" not in href):
                    continue

                title  = li.select_text("span")
                poster = li.select_attr("img", "data-src")

                if title and href:
                    results.append(SearchResult(
                        title  = title.strip(),
                        url    = self.fix_url(href),
                        poster = self.fix_url(poster),
                    ))
        except Exception:
            pass

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url, headers={"Referer": self.main_url})
        secici = HTMLHelper(istek.text)

        title_el  = secici.select_first("div.page-title h1 a")
        title     = title_el.text(strip=True) if title_el else ""
        org_title = secici.select_text("div.page-title p") or ""
        if org_title and org_title != title:
            title = f"{title} - {org_title}"

        poster      = secici.select_attr("div.series-profile-image img", "src")
        year        = secici.regex_first(r"\((\d{4})\)", secici.select_text("h1 span"))
        rating      = secici.select_text("span.color-imdb")
        description = secici.select_text("div.series-profile-summary p")
        tags        = secici.select_texts("div.series-profile-type a")
        actors      = []
        for cast in secici.select("div.series-profile-cast li"):
            name = cast.select_text("h5.truncate")
            if name:
                actors.append(name.strip())

        if "/dizi/" in url:
            episodes = []
            szn      = 1
            for sezon in secici.select("div.series-profile-episode-list"):
                blm = 1
                for bolum in sezon.select("li"):
                    ep_name = bolum.select_text("h6.truncate a")
                    ep_href = bolum.select_attr("h6.truncate a", "href")
                    if not ep_name or not ep_href:
                        continue

                    episodes.append(Episode(
                        season  = szn,
                        episode = blm,
                        title   = ep_name,
                        url     = self.fix_url(ep_href),
                    ))
                    blm += 1
                szn += 1

            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = title,
                description = description,
                tags        = tags,
                year        = year,
                actors      = actors,
                rating      = rating,
                episodes    = episodes,
            )

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            year        = year,
            actors      = actors,
            rating      = rating,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        # ci_session cookie al
        init_resp = await self.httpx.get(self.main_url)
        ci_cookie = init_resp.cookies.get("ci_session", "")

        istek  = await self.httpx.get(
            url,
            headers = {"Referer": f"{self.main_url}/"},
            cookies = {"ci_session": ci_cookie} if ci_cookie else {},
        )
        secici = HTMLHelper(istek.text)

        iframe_src = secici.select_attr("div#tv-spoox2 iframe", "src")
        if not iframe_src:
            return []

        iframe_src  = self.fix_url(iframe_src)
        iframe_resp = await self.httpx.get(iframe_src, headers={"Referer": f"{self.main_url}/"})

        response = []

        # bePlayer pattern — CryptoJS decrypt
        be_match = re.search(r"bePlayer\('([^']+)',\s*'(\{[^}]+\})'\)", iframe_resp.text)
        if be_match:
            pass_val = be_match.group(1)
            data_val = be_match.group(2)

            try:
                decrypted = AESManager.decrypt(data_val, pass_val)
                data      = json.loads(decrypted)
                m3u8_url  = data.get("video_location", "")

                subtitles = []
                for sub in data.get("strSubtitles", []):
                    sub_file  = sub.get("file", "")
                    sub_label = sub.get("label", "")
                    if sub_file and "Forced" not in sub_label:
                        subtitles.append(self.new_subtitle(self.fix_url(sub_file), sub_label))

                if m3u8_url:
                    response.append(ExtractResult(
                        name      = self.name,
                        url       = m3u8_url,
                        referer   = iframe_src,
                        subtitles = subtitles,
                    ))
            except Exception:
                pass

        # Fallback: loadExtractor
        data = await self.extract(iframe_src, referer=f"{self.main_url}/")
        self.collect_results(response, data)

        return self.deduplicate(response)
