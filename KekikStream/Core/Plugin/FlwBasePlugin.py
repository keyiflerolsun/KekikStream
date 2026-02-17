# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

"""
FLW sitesi temalı plugin'ler (Watch32, Zoechip vb.) için ortak base class.

Bu siteler aynı frontend template'i kullanır:
- div.flw-item kartları
- AJAX season/episode API'leri
- div.detail_page-watch ile content ID
"""

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper


class FlwBasePlugin(PluginBase):
    """
    FLW template kullanan siteler için ortak base class.

    Alt sınıflarda sadece şunları tanımlamanız yeterli:
        name, language, main_url, description, main_page
    """

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}{page}")
        secici = HTMLHelper(istek.text)

        return [
            MainPageResult(
                category = category,
                title    = veri.select_attr("h2.film-name a", "title"),
                url      = self.fix_url(veri.select_attr("h2.film-name a", "href")),
                poster   = self.fix_url(veri.select_attr("img.film-poster-img", "data-src"))
            )
                for veri in secici.select("div.flw-item")
        ]

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/search/{query.replace(' ', '-')}")
        secici = HTMLHelper(istek.text)

        return [
            SearchResult(
                title  = veri.select_attr("h2.film-name a", "title"),
                url    = self.fix_url(veri.select_attr("h2.film-name a", "href")),
                poster = self.fix_url(veri.select_attr("img.film-poster-img", "data-src"))
            )
                for veri in secici.select("div.flw-item")
        ]

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        content_id  = secici.select_attr("div.detail_page-watch", "data-id")
        details     = secici.select_first("div.detail_page-infor") or secici.select_first("div.m_i-detail")
        name        = details.select_text("h2.heading-name > a") if details else ""
        poster      = details.select_poster("div.film-poster > img") if details else None
        description = details.select_text("div.description") if details else ""
        year        = str(secici.extract_year())
        tags        = secici.meta_list("Genre", container_selector="div.row-line")
        rating      = secici.select_text("button.btn-imdb")
        rating      = rating.replace("N/A", "").split(":")[-1].strip() if rating else None
        actors      = secici.meta_list("Casts", container_selector="div.row-line")

        common_info = {
            "url"         : url,
            "poster"      : self.fix_url(poster),
            "title"       : name,
            "description" : description,
            "tags"        : tags,
            "rating"      : rating,
            "year"        : year,
            "actors"      : actors
        }

        if "movie" in url:
            return MovieInfo(**common_info)

        seasons_resp = await self.httpx.get(f"{self.main_url}/ajax/season/list/{content_id}")
        sh           = HTMLHelper(seasons_resp.text)

        episodes = []
        for season in sh.select("a.dropdown-item"):
            season_id = season.attrs.get("data-id")
            s_val, _  = sh.extract_season_episode(season.text())

            e_resp = await self.httpx.get(f"{self.main_url}/ajax/season/episodes/{season_id}")
            eh     = HTMLHelper(e_resp.text)

            for ep in eh.select("a.eps-item"):
                ep_id    = ep.attrs.get("data-id")
                ep_title = ep.attrs.get("title", "")
                _, e_val = eh.extract_season_episode(ep_title)

                episodes.append(Episode(
                    season  = s_val or 1,
                    episode = e_val or 1,
                    title   = ep_title,
                    url     = f"servers/{ep_id}"
                ))

        return SeriesInfo(**common_info, episodes=episodes)

    async def load_links(self, url: str) -> list[ExtractResult]:
        if "servers/" in url:
            servers_url = f"servers/{url.split('/')[-1]}"
        elif "list/" in url:
            servers_url = f"list/{url.split('/')[-1]}"
        else:
            istek      = await self.httpx.get(url)
            secici     = HTMLHelper(istek.text)
            content_id = secici.select_attr("div.detail_page-watch", "data-id")
            if not content_id:
                return []

            servers_url = f"list/{content_id}"

        servers_resp = await self.httpx.get(f"{self.main_url}/ajax/episode/{servers_url}")
        sh           = HTMLHelper(servers_resp.text)

        results = []
        for server in sh.select("a.link-item"):
            server_name = server.text(strip=True)
            link_id     = server.attrs.get("data-linkid") or server.attrs.get("data-id")
            source_resp = await self.httpx.get(f"{self.main_url}/ajax/episode/sources/{link_id}")
            video_url   = source_resp.json().get("link")

            if video_url:
                data = await self.extract(video_url, name_override=server_name)
                if data:
                    self.collect_results(results, data)
                else:
                    results.append(ExtractResult(url=video_url, name=f"{self.name} | {server_name}"))

        return results
