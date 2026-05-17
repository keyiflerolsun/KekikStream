# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re

class Turkish123(PluginBase):
    name        = "Turkish123"
    language    = "tr"
    main_url    = "https://turkish123.ac"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Watch Turkish Series with English Subtitles Online for Free without Registration only at our website - turkish123.ac"

    main_page   = {
        f"{main_url}/series-list/page/"     : "Series List",
        f"{main_url}/episodes-list/page/"   : "Episodes List",
        f"{main_url}/genre/action/page/"    : "Action",
        f"{main_url}/genre/adventure/page/" : "Adventure",
        f"{main_url}/genre/comedy/page/"    : "Comedy",
        f"{main_url}/genre/crime/page/"     : "Crime",
        f"{main_url}/genre/drama/page/"     : "Drama",
        f"{main_url}/genre/family/page/"    : "Family",
        f"{main_url}/genre/history/page/"   : "History",
        f"{main_url}/genre/mystery/page/"   : "Mystery",
        f"{main_url}/genre/romance/page/"   : "Romance",
        f"{main_url}/genre/thriller/page/"  : "Thriller",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        full_url = f"{url}{page}"
        istek    = await self.async_cf_get(full_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.ml-item"):
            title  = veri.select_text("h2") or veri.select_attr("a", "title")
            href   = veri.select_attr("a", "href")
            poster = veri.select_attr("img", "src") or veri.select_attr("img", "data-src")

            if title and href:
                # Remove episode suffix from URL if present for series result
                if "-episode" in href:
                    href = href.split("-episode")[0]

                results.append(MainPageResult(
                    category = category,
                    title    = title.strip(),
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.async_cf_get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.ml-item"):
            title  = item.select_text("h2") or item.select_attr("a", "title")
            href   = item.select_attr("a", "href")
            poster = item.select_attr("img", "src") or item.select_attr("img", "data-src")

            if title and href:
                if "-episode" in href:
                    href = href.split("-episode")[0]

                results.append(SearchResult(
                    title  = title.strip(),
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> SeriesInfo | MovieInfo:
        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("h1[itemprop=name]") or secici.select_text("h1")
        poster      = secici.select_poster("div.thumb.mvic-thumb img") or secici.meta_value("og:image")
        description = secici.select_text("p.f-desc") or secici.select_text("div.description")
        tags        = secici.meta_list("Genre", container_selector="div.mvici-left") or secici.select_texts("div.genres a")
        year        = secici.meta_value("Year", container_selector="div.mvici-right") or secici.extract_year()
        actors      = secici.meta_list("Actors", container_selector="div.mvici-left") or secici.select_texts("div.actors a")
        rating      = secici.select_text("span.imdb-r") or secici.select_text(".imdb-rating")

        ep_links = secici.select("div.les-content a")
        if ep_links:
            episodes = []
            for ep in ep_links:
                ep_url   = ep.attrs.get("href")
                # Title often contains Season info in a span, so select_direct_text is better
                ep_title = ep.select_direct_text() or ep.text(strip=True)
                if ep_url:
                    s, e = secici.extract_season_episode(ep_title)
                    episodes.append(Episode(
                        season  = s,
                        episode = e,
                        title   = ep_title.strip(),
                        url     = self.fix_url(ep_url)
                    ))

            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = title.strip() if title else "",
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
            title       = title.strip() if title else "",
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        api_url     = "http://px-webservisler:2585/api/v1/turkish123"
        response    = []
        tasks       = []
        api_success = False

        try:
            params = {"url": url}
            resp   = await self.httpx.get(api_url, params=params, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success") and data.get("results"):
                    for item in data["results"]:
                        tasks.append((self.fix_url(item["url"]), item["name"]))
                    api_success = True
        except Exception:
            pass

        # Fallback to local regex scraping if API failed
        if not api_success:
            istek = await self.async_cf_get(url)
            text  = istek.text

            # 1. Klasik iframeleri tara
            iframes = re.findall(r'<iframe.*?src=["\'](\S+?)["\']', text)
            for ifr in iframes:
                tasks.append((self.fix_url(ifr), "Iframe"))

            # Eğer hiç bulunamazsa sayfadaki diğer linkleri tara
            if not tasks:
                secici = HTMLHelper(text)
                for a in secici.select("a"):
                    href = a.attrs.get("href")
                    if href and any(x in href.lower() for x in ["mixdrop", "doodstream", "vidmoly", "vidoza", "streamtape"]):
                        tasks.append((self.fix_url(href), "Server"))

        # Taskları paralel olarak çalıştır
        extract_tasks = [self.extract(task_url, referer=url) for task_url, _ in tasks]
        results       = await self.gather_with_limit(extract_tasks)

        for (task_url, server_name), data in zip(tasks, results):
            if data:
                if isinstance(data, list):
                    for item in data:
                        item.name       = f"{server_name}"
                        item.referer    = url
                        item.user_agent = self.httpx.headers.get("User-Agent")
                else:
                    data.name       = f"{server_name}"
                    data.referer    = url
                    data.user_agent = self.httpx.headers.get("User-Agent")
                self.collect_results(response, data)
            else:
                response.append(ExtractResult(
                    url        = task_url,
                    name       = f"{server_name}",
                    referer    = url,
                    user_agent = self.httpx.headers.get("User-Agent")
                ))

        return response
