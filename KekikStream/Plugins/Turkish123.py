# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re

class Turkish123(PluginBase):
    name        = "Turkish123"
    language    = "tr"
    main_url    = "https://ahs.turkish123.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Turkish123 - Watch Turkish Series with English Subtitles Online for Free without Registration only at our website - turkish123.com"

    main_page   = {
        f"{main_url}/series-list/page/"    : "Series List",
        f"{main_url}/episodes-list/page/"  : "Episodes List",
        f"{main_url}/genre/action/page/"   : "Action",
        f"{main_url}/genre/comedy/page/"   : "Comedy",
        f"{main_url}/genre/drama/page/"    : "Drama",
        f"{main_url}/genre/history/page/"  : "History",
        f"{main_url}/genre/romance/page/"  : "Romance",
        f"{main_url}/genre/thriller/page/" : "Thriller",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}{page}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movies-list div.ml-item"):
            title  = veri.select_text("h2")
            href   = veri.select_attr("a", "href")
            poster = veri.select_attr("img", "src")

            if title and href:
                # Remove episode suffix from URL if present for series result
                if "-episode" in href:
                    href = href.split("-episode")[0]

                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.movies-list div.ml-item"):
            title  = item.select_text("h2")
            href   = item.select_attr("a", "href")
            poster = item.select_attr("img", "src")

            if title and href:
                if "-episode" in href:
                    href = href.split("-episode")[0]

                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> SeriesInfo | MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("h1[itemprop=name]")
        poster      = secici.select_attr("div.thumb.mvic-thumb img", "src")
        description = secici.select_text("p.f-desc")
        tags        = secici.meta_list("Genre", container_selector="div.mvici-left")
        year        = secici.meta_value("Year", container_selector="div.mvici-right")
        actors      = secici.meta_list("Actors", container_selector="div.mvici-left")
        rating      = secici.select_text("span.imdb-r")

        ep_links = secici.select("div.les-content a")
        if ep_links:
            episodes = []
            for ep in ep_links:
                ep_url   = ep.select_attr(None, "href")
                ep_title = ep.select_text()
                if ep_url:
                    episodes.append(Episode(
                        title = ep_title,
                        url   = self.fix_url(ep_url)
                    ))

            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = title,
                description = description,
                tags        = tags,
                rating      = rating,
                year        = year,
                actors      = actors,
                episodes    = episodes
            )

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)

        # Regex for iframe: <iframe.*src=["|'](\S+)["|']\s
        iframes = re.findall(r'<iframe.*?src=["\'](\S+?)["\']', istek.text)

        response = []
        tasks    = []
        for iframe in iframes:
            tasks.append(self.extract(self.fix_url(iframe)))

        for data in await self.gather_with_limit(tasks):
            self.collect_results(response, data)

        return response
