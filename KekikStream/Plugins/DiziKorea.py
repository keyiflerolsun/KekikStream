# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re

class DiziKorea(PluginBase):
    name        = "DiziKorea"
    language    = "tr"
    main_url    = "https://dizikorea3.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Kore Dizileri izle, Dizikorea size en yeni ve güncel romantik komedi, okul tarzında ki Kore Asya Dizilerini Full HD Türkçe Altyazılı izleme şansı verir."

    main_page   = {
        f"{main_url}/sayfa/tum-kore-dizileri/" : "Kore Dizileri",
        f"{main_url}/sayfa/kore-filmleri-izle1/": "Kore Filmleri",
        f"{main_url}/dizi/tur/dram/"           : "Dram Dizileri",
        f"{main_url}/dizi/tur/komedi/"         : "Komedi Dizileri",
        f"{main_url}/dizi/tur/romantik/"       : "Romantik Diziler",
        f"{main_url}/dizi/tur/aksiyon/"        : "Aksiyon Dizileri",
        f"{main_url}/dizi/tur/gizem/"          : "Gizem Dizileri",
        f"{main_url}/dizi/tur/suc/"            : "Suç Dizileri",
        f"{main_url}/sayfa/tayland-dizileri/"   : "Tayland Dizileri",
        f"{main_url}/sayfa/tayland-filmleri/"   : "Tayland Filmleri",
        f"{main_url}/sayfa/cin-dizileri/"       : "Çin Dizileri",
        f"{main_url}/sayfa/cin-filmleri/"       : "Çin Filmleri",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}{page}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.poster-long"):
            title  = veri.select_text("h2")
            href   = veri.select_attr("a", "href")
            poster = veri.select_attr("div.poster-long-image img.lazy", "data-src")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title.strip(),
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek = await self.httpx.post(
            f"{self.main_url}/search",
            data    = {"query": query},
            headers = {"X-Requested-With": "XMLHttpRequest"},
        )

        results = []
        try:
            data = istek.json()
            html   = data.get("theme", "")
            secici = HTMLHelper(html)

            for li in secici.select("ul li"):
                href = li.select_attr("a", "href")
                if not href or ("/dizi/" not in href and "/film/" not in href):
                    continue

                title  = li.select_text("span")
                poster = li.select_attr("img.lazy", "data-src")

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
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("h1 a") or ""
        poster      = secici.select_attr("meta[property=\"og:image\"]", "content")
        year        = secici.regex_first(r"\((\d{4})\)", secici.select_text("h1 span"))
        description = secici.select_text("div.series-profile-summary p")
        tags        = secici.select_texts("div.series-profile-type a")

        actors = []
        for cast in secici.select("div.series-profile-cast li"):
            name = cast.select_text("h5")
            if name:
                actors.append(name.strip())

        if "/dizi/" in url:
            episodes = []
            for ep_list in secici.select("div.series-profile-episode-list"):
                parent_id = ep_list.parent.attrs.get("id", "") if ep_list.parent else ""
                szn       = 1
                szn_match = re.search(r"(\d+)$", parent_id)
                if szn_match:
                    szn = int(szn_match.group(1))

                for bolum in ep_list.select("li"):
                    ep_href    = bolum.select_attr("h6 a", "href")
                    ep_num     = bolum.select_text("a.truncate data")
                    ep_episode = int(ep_num) if ep_num and ep_num.isdigit() else None
                    if not ep_href:
                        continue

                    episodes.append(Episode(
                        season  = szn,
                        episode = ep_episode,
                        title   = f"{szn}. Sezon {ep_episode}. Bölüm",
                        url     = self.fix_url(ep_href),
                    ))

            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = title,
                description = description,
                tags        = tags,
                year        = year,
                actors      = actors,
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
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        iframes = []
        for btn in secici.select("div.video-services button"):
            iframe_src = btn.attrs.get("data-hhs")
            if iframe_src:
                iframes.append(self.fix_url(iframe_src))

        tasks    = [self.extract(url, referer=f"{self.main_url}/") for url in iframes]
        response = []
        for data in await self.gather_with_limit(tasks):
            self.collect_results(response, data)

        return self.deduplicate(response)
