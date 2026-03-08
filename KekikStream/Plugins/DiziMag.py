# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
from Kekik.Sifreleme  import AESManager
import re, json

class DiziMag(PluginBase):
    name        = "DiziMag"
    language    = "tr"
    main_url    = "https://dizimag.onl"
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
        for cast in secici.select('ul[scrollable="true"] h5, .series-profile-cast li h5'):
            actors.append(cast.text(strip=True))

        if "/dizi/" in url:
            episodes = []
            for sezon in secici.select(".series-profile-episode-list"):
                # Sezon numarasını id'den çek: sea-1 -> 1
                sezon_parent = sezon.parent
                s_id         = sezon_parent.attributes.get("id") if sezon_parent else ""
                s_val        = int(s_id.split("-")[-1]) if s_id and "-" in s_id else 1

                for bolum in sezon.select("li"):
                    ep_link = bolum.select_first("div.series-profile-episode-list-left a.truncate")
                    ep_name = bolum.select_text("h6.truncate a") or (ep_link.text(strip=True) if ep_link else "")
                    ep_href = ep_link.attrs.get("href") if ep_link else ""
                    if not ep_href:
                        continue

                    _, e_val = secici.extract_season_episode(ep_href)

                    episodes.append(Episode(
                        season  = s_val,
                        episode = e_val or 1,
                        title   = ep_name or f"Bölüm {e_val}",
                        url     = self.fix_url(ep_href),
                    ))

            if episodes:
                last_episode = episodes[-1]
                with_ready   = await self.httpx.get(last_episode.url, headers={"Referer": self.main_url})
                if "this-episode-not-ready" in with_ready.text or "çok yakında yayınlanacak" in with_ready.text.lower():
                    episodes.pop()

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
        istek  = await self.httpx.get(url, headers={"Referer": self.main_url})
        secici = HTMLHelper(istek.text)

        response     = []
        extract_args = []

        for tab in secici.select("ul.tab.alternative-group li[data-number]"):
            tab_hash = tab.attrs.get("data-group-hash")
            tab_name = tab.select_text(None) or ""

            if not tab_hash:
                continue

            group_resp = await self.httpx.post(
                url     = f"{self.main_url}/get/video/group",
                headers = {
                    "X-Requested-With" : "XMLHttpRequest",
                    "Content-Type"     : "application/x-www-form-urlencoded; charset=UTF-8",
                    "Referer"          : url,
                },
                data    = {"hash": tab_hash},
            )

            try:
                payload = group_resp.json()
            except Exception:
                payload = {}

            videos = payload.get("videos", []) if payload.get("success") else []
            for video in videos:
                video_url   = self.fix_url(video.get("link", ""))
                server_name = video.get("name", "") or tab_name
                if video_url:
                    extract_args.append((video_url, f"{tab_name} | {server_name}" if tab_name else server_name))

        if not extract_args:
            for server in secici.select("div.video-services button[data-hhs], div.video-services button[data-frame]"):
                server_name = server.attrs.get("title") or server.text(strip=True)
                video_url   = server.attrs.get("data-hhs") or server.attrs.get("data-frame")

                if video_url:
                    extract_args.append((self.fix_url(video_url), server_name))

        tasks = [self.extract(video_url, name_override=server_name or None) for video_url, server_name in extract_args]
        for data in await self.gather_with_limit(tasks):
            self.collect_results(response, data)

        return self.deduplicate(response)
