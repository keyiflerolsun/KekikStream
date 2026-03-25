# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper

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
        f"{main_url}/genre/comedy?page="           : "Comedy",
        f"{main_url}/genre/crime?page="            : "Crime",
        f"{main_url}/genre/documentary?page="      : "Documentary",
        f"{main_url}/genre/drama?page="            : "Drama",
        f"{main_url}/genre/family?page="           : "Family",
        f"{main_url}/genre/fantasy?page="          : "Fantasy",
        f"{main_url}/genre/history?page="          : "History",
        f"{main_url}/genre/horror?page="           : "Horror",
        f"{main_url}/genre/mystery?page="          : "Mystery",
        f"{main_url}/genre/romance?page="          : "Romance",
        f"{main_url}/genre/science-fiction?page="  : "Science Fiction",
        f"{main_url}/genre/thriller?page="         : "Thriller",
        f"{main_url}/genre/war?page="              : "War",
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

        title       = secici.select_text("div.dp-i-content h2 a")
        poster      = secici.select_attr("meta[property='og:image']", "content")
        description = secici.select_attr("meta[property='og:description']", "content")
        tags        = secici.select_texts("div.row-line a[href*='/genre/']")
        actors      = secici.select_texts("div.row-line a[href*='/cast/']")

        year = None
        for row in secici.select("div.row-line"):
            text = row.text()
            if "Released:" in text:
                year = text.split("Released:")[-1].strip().split("-")[0].strip()
                break

        duration = None
        for row in secici.select("div.row-line"):
            text = row.text()
            if "Duration:" in text:
                duration = text.split("Duration:")[-1].replace("min", "").strip()
                break

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
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
