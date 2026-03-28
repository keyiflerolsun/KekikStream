# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re


class JPFilms(PluginBase):
    name        = "JPFilms"
    language    = "en"
    main_url    = "https://jp-films.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Watch online The Legend of Love & Sincerity on Japanese Classic Movies and TVSeries (https://jp-films.com) with English Subtitle. Japanese Classic Movies, Japanese Classic TVSeries, Jindaigeki, Action, Tora-san, Zatoichi"

    main_page = {
        f"{main_url}/movies/"                                                   : "Latest Movies",
        f"{main_url}/tv-series/"                                                : "Latest Series",
        f"{main_url}/filter-movies/sort/formality/status/country/release/20/"   : "Action",
        f"{main_url}/filter-movies/sort/formality/status/country/release/2659/" : "Action & Adventure",
        f"{main_url}/filter-movies/sort/formality/status/country/release/295/"  : "Adventure",
        f"{main_url}/filter-movies/sort/formality/status/country/release/3015/" : "Animation",
        f"{main_url}/filter-movies/sort/formality/status/country/release/56/"   : "Comedy",
        f"{main_url}/filter-movies/sort/formality/status/country/release/4/"    : "Crime",
        f"{main_url}/filter-movies/sort/formality/status/country/release/1055/" : "Documentary",
        f"{main_url}/filter-movies/sort/formality/status/country/release/5/"    : "Drama",
        f"{main_url}/filter-movies/sort/formality/status/country/release/920/"  : "Family",
        f"{main_url}/filter-movies/sort/formality/status/country/release/894/"  : "Fantasy",
        f"{main_url}/filter-movies/sort/formality/status/country/release/619/"  : "History",
        f"{main_url}/filter-movies/sort/formality/status/country/release/258/"  : "Horror",
        f"{main_url}/filter-movies/sort/formality/status/country/release/71/"   : "Jidaigeki",
        f"{main_url}/filter-movies/sort/formality/status/country/release/11/"   : "Mystery",
        f"{main_url}/filter-movies/sort/formality/status/country/release/281/"  : "Romance",
        f"{main_url}/filter-movies/sort/formality/status/country/release/318/"  : "Science Fiction",
        f"{main_url}/filter-movies/sort/formality/status/country/release/119/"  : "Thriller",
        f"{main_url}/filter-movies/sort/formality/status/country/release/249/"  : "War",
        f"{main_url}/filter-movies/sort/formality/status/country/release/1729/" : "Western",
        f"{main_url}/filter-movies/sort/formality/status/country/release/32/"   : "Yakuza",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        full_url = url if page <= 1 else f"{url.rstrip('/')}/page/{page}/"
        istek    = await self.httpx.get(full_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for item in secici.select("article.thumb.grid-item"):
            link   = item.select_first("a.halim-thumb")
            title  = item.select_text("h2.entry-title")
            href   = link.attrs.get("href") if link else None
            poster = item.select_poster("img")

            if title and href:
                results.append(MainPageResult(category=category, title=title.strip(), url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        full_url = f"{self.main_url}/search/{query}"
        istek    = await self.httpx.get(full_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for item in secici.select("article.thumb.grid-item"):
            link   = item.select_first("a.halim-thumb")
            title  = item.select_text("h2.entry-title")
            href   = link.attrs.get("href") if link else None
            poster = item.select_poster("img")

            if title and href:
                results.append(SearchResult(title=title.strip(), url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        raw_title   = secici.select_text("h1.entry-title")
        title       = re.sub(r"\s*\(\d{4}\)$", "", raw_title) if raw_title else "Bilinmeyen"
        poster      = secici.select_attr(".movie-thumb img", "src") or secici.select_attr("meta[property='og:image']", "content")
        description = secici.select_text("article.item-content")

        # Meta verileri
        year   = secici.extract_year(".released a[href*='release']")
        tags   = secici.select_texts(".category a[href*='genres']")
        rating = secici.select_text(".halim_imdbrating .score")
        actors = secici.select_texts(".actors a")

        episodes = []
        # Hem dizi bölümlerini hem de tekli film linklerini yakala
        items = secici.select(".halim-list-eps li, .halim-watch-box a.watch-movie")

        seen_urls = set()
        for item in items:
            link = item.select_first("a") or item
            span = item.select_first("span")
            href = self.fix_url(link.attrs.get("href") or (span.attrs.get("data-href") if span else None))
            name = (span.text(strip=True) if span else link.text(strip=True)) or "Watch"

            if href and href not in seen_urls:
                seen_urls.add(href)
                num_match = re.search(r"(\d+)", name)
                ep_num    = int(num_match.group(1)) if num_match else len(episodes) + 1

                episodes.append(Episode(season=1, episode=ep_num, title=name, url=href))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title.strip(),
            description = description,
            tags        = tags,
            year        = str(year) if year else None,
            rating      = rating,
            actors      = actors,
            episodes    = episodes,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        buttons          = secici.select(".halim-list-eps .halim-btn")
        current_ep_match = re.search(r"(ep-\d+)", url)
        current_slug     = current_ep_match.group(1) if current_ep_match else None

        response = []
        tasks    = []

        async def fetch_source(slug, server_id, post_id):
            ajax_url = f"{self.main_url}/wp-content/themes/halimmovies/player.php"
            try:
                resp = await self.httpx.get(
                    ajax_url,
                    params  = {"episode_slug": slug, "server_id": server_id, "post_id": post_id},
                    headers = {"X-Requested-With": "XMLHttpRequest", "Referer": url},
                )
                data        = resp.json()
                source_html = data.get("data", {}).get("sources", "")
                if source_html:
                    m3u8_url = HTMLHelper(source_html).select_attr("source", "src")
                    if m3u8_url:
                        return ExtractResult(name=self.name, url=self.fix_url(m3u8_url), referer=f"{self.main_url}/")
            except:
                pass
            return None

        for btn in buttons:
            slug      = btn.attrs.get("data-episode-slug")
            server_id = btn.attrs.get("data-server")
            post_id   = btn.attrs.get("data-post-id")

            if slug and server_id and post_id:
                if current_slug is None or slug == current_slug or "movie" in slug.lower():
                    tasks.append(fetch_source(slug, server_id, post_id))

        results = await self.gather_with_limit(tasks)
        for res in results:
            if res:
                response.append(res)

        return response
