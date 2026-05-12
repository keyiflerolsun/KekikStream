# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re
import base64

class BFlix(PluginBase):
    name        = "BFlix"
    language    = "en"
    main_url    = "https://bflix.sh"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Watch free Streaming movies and TV shows online in HD quality."

    main_page   = {
        f"{main_url}/movie?page="        : "Movies",
        f"{main_url}/tv-show?page="      : "TV Shows",
        f"{main_url}/top-imdb?page="     : "Top IMDB",
        f"{main_url}/genre/action?page=" : "Action",
        f"{main_url}/genre/comedy?page=" : "Comedy",
        f"{main_url}/genre/horror?page=" : "Horror",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        full_url = f"{url}{page}"
        istek    = await self.async_cf_get(full_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.film, div.film-inner"):
            title  = item.select_text("h2.film-name") or item.select_text("a.film-name") or item.select_attr("a", "title")
            href   = item.select_attr("a", "href")
            img    = item.select_first("img")
            poster = img.select_attr(None, "data-src") or img.select_attr(None, "src") if img else None

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title.strip(),
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        target_url = f"{self.main_url}/search/{query.replace(' ', '-')}"
        istek      = await self.async_cf_get(target_url)
        secici     = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.film, div.film-inner"):
            title  = item.select_text("h2.film-name") or item.select_text("a.film-name") or item.select_attr("a", "title")
            href   = item.select_attr("a", "href")
            img    = item.select_first("img")
            poster = img.select_attr(None, "data-src") or img.select_attr(None, "src") if img else None

            if title and href:
                results.append(SearchResult(
                    title  = title.strip(),
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("h2.heading-name") or secici.select_text("h1")
        poster      = secici.select_poster("img.film-poster-img") or secici.meta_value("og:image")
        description = secici.select_text("div.description") or secici.meta_value("og:description")

        meta   = secici.select("div.elements div.row-line")
        year   = None
        rating = None
        for row in meta:
            label = row.select_text("strong")
            if label:
                if "Released" in label:
                    year = row.select_text("span")
                if "IMDb" in label:
                    rating = row.select_text("span")

        tags   = secici.select_texts("div.elements div.row-line:contains('Genre') a")
        actors = secici.select_texts("div.elements div.row-line:contains('Casts') a")

        is_series = "/tv/" in url or "/series/" in url
        if is_series:
            episodes = []
            # AJAX URL'sini bul
            ajax_url = secici.regex_first(r"const current_url = '([^']+)'")
            if ajax_url:
                ajax_istek  = await self.async_cf_get(ajax_url, headers={"Referer": url})
                ajax_secici = HTMLHelper(ajax_istek.text)
                for li in ajax_secici.select("li"):
                    a_tag = li.select_first("a")
                    if a_tag:
                        ep_href = a_tag.attrs.get("href")
                        ep_name = a_tag.text(strip=True)
                        s, e = secici.extract_season_episode(ep_name)
                        episodes.append(Episode(
                            season  = s or 1,
                            episode = e or 1,
                            title   = ep_name,
                            url     = self.fix_url(ep_href)
                        ))

            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = title.strip() if title else "",
                description = description,
                tags        = tags,
                year        = year,
                rating      = rating,
                actors      = actors,
                episodes    = episodes
            )

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title.strip() if title else "",
            description = description,
            tags        = tags,
            year        = year,
            rating      = rating,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        # Flw clones often have a data-id or similar
        # For bflix.sh, it's a bit different.
        # I'll just look for any iframe as a start.
        response = []
        for iframe in secici.select("iframe"):
            src = iframe.attrs.get("src")
            if src:
                data = await self.extract(self.fix_url(src), referer=url)
                if data:
                    self.collect_results(response, data)
                else:
                    response.append(ExtractResult(url=self.fix_url(src), name="Iframe", referer=url))

        return self.deduplicate(response)
