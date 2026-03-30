# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper
import re

class Watch2Movies(PluginBase):
    name        = "Watch2Movies"
    language    = "en"
    main_url    = "https://watch2movies.net"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Watch Your Favorite Movies & TV Shows Online - Streaming For Free. With Movies & TV Shows 4k, 2k, Full HD… Find Your Movies & Watch NOW!"

    main_page   = {
        f"{main_url}/genre/action?page="           : "Action",
        f"{main_url}/genre/action-adventure?page=" : "Action & Adventure",
        f"{main_url}/genre/adventure?page="        : "Adventure",
        f"{main_url}/genre/animation?page="        : "Animation",
        f"{main_url}/genre/biography?page="        : "Biography",
        f"{main_url}/genre/comedy?page="           : "Comedy",
        f"{main_url}/genre/crime?page="            : "Crime",
        f"{main_url}/genre/documentary?page="      : "Documentary",
        f"{main_url}/genre/drama?page="            : "Drama",
        f"{main_url}/genre/family?page="           : "Family",
        f"{main_url}/genre/fantasy?page="          : "Fantasy",
        f"{main_url}/genre/history?page="          : "History",
        f"{main_url}/genre/horror?page="           : "Horror",
        f"{main_url}/genre/kids?page="             : "Kids",
        f"{main_url}/genre/music?page="            : "Music",
        f"{main_url}/genre/mystery?page="          : "Mystery",
        f"{main_url}/genre/news?page="             : "News",
        f"{main_url}/genre/reality?page="          : "Reality",
        f"{main_url}/genre/romance?page="          : "Romance",
        f"{main_url}/genre/sci-fi-fantasy?page="   : "Sci-Fi & Fantasy",
        f"{main_url}/genre/science-fiction?page="  : "Science Fiction",
        f"{main_url}/genre/soap?page="             : "Soap",
        f"{main_url}/genre/talk?page="             : "Talk",
        f"{main_url}/genre/thriller?page="         : "Thriller",
        f"{main_url}/genre/tv-movie?page="         : "TV Movie",
        f"{main_url}/genre/war?page="              : "War",
        f"{main_url}/genre/war-politics?page="     : "War & Politics",
        f"{main_url}/genre/western?page="          : "Western",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}{page}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.flw-item"):
            title  = veri.select_text("h2 a")
            href   = veri.select_attr("a", "href")
            poster = veri.select_attr("img", "data-src")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/search/{query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.flw-item"):
            title  = veri.select_text("h2 a")
            href   = veri.select_attr("a", "href")
            poster = veri.select_attr("img", "data-src")

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        details     = secici.select_first("div.detail_page-infor") or secici.select_first("div.m_i-detail")
        title       = secici.select_text("div.dp-i-content h2 a") or (details.select_text("h2.heading-name > a") if details else None)
        poster      = secici.select_attr("meta[property='og:image']", "content") or (details.select_poster("div.film-poster > img") if details else None)
        description = secici.select_attr("meta[property='og:description']", "content") or (details.select_text("div.description") if details else None)
        tags        = secici.select_texts("div.row-line a[href*='/genre/']")
        actors      = secici.select_texts("div.row-line a[href*='/cast/']")

        if not tags and details:
            tags = secici.meta_list("Genre", container_selector="div.row-line")

        if not actors and details:
            actors = secici.meta_list("Casts", container_selector="div.row-line")

        rating = secici.select_text("button.btn-imdb")
        rating = rating.replace("N/A", "").split(":")[-1].strip() if rating else None

        year = None
        for row in secici.select("div.row-line"):
            text = row.text()
            if "Released:" in text:
                year_match = re.search(r"Released:\s*(\d{4})", text)
                if year_match:
                    year = year_match.group(1)
                break

        if not year:
            extracted_year = secici.extract_year()
            year           = str(extracted_year) if extracted_year else None

        duration = None
        for row in secici.select("div.row-line"):
            text = row.text()
            if "Duration:" in text:
                duration_match = re.search(r"Duration:\s*(\d+)", text)
                if duration_match:
                    duration = int(duration_match.group(1))
                break

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors,
            duration    = duration,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        ep_id = url.rstrip("/").split("-")[-1]

        istek  = await self.httpx.get(f"{self.main_url}/ajax/episode/list/{ep_id}", headers={"Referer": url})
        secici = HTMLHelper(istek.text)

        data_ids = []
        for link in secici.select("li.nav-item a"):
            data_id = link.attrs.get("data-id", "")
            if data_id:
                data_ids.append(data_id)

        async def _fetch_and_extract(data_id):
            try:
                src_resp = await self.httpx.get(
                    f"{self.main_url}/ajax/episode/sources/{data_id}",
                    headers = {"X-Requested-With": "XMLHttpRequest", "Referer": url},
                )
                embed_link = src_resp.json().get("link", "")
                if embed_link:
                    return await self.extract(embed_link, referer=f"{self.main_url}/")
            except Exception:
                pass
            return None

        tasks    = [_fetch_and_extract(did) for did in data_ids]
        response = []
        for data in await self.gather_with_limit(tasks):
            self.collect_results(response, data)

        return response
