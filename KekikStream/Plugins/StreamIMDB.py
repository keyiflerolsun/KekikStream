# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re, json

class StreamIMDB(PluginBase):
    name        = "StreamIMDB"
    language    = "en"
    main_url    = "https://streamimdb.ru"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Browse thousands of free movies & TV shows! Updated daily with HD content."

    main_page   = {
        f"{main_url}/trending"                 : "Trending",
        f"{main_url}/popular"                  : "Popular",
        f"{main_url}/movies"                   : "Movies",
        f"{main_url}/tv-shows"                 : "TV Shows",
        f"{main_url}/category/action"          : "Action",
        f"{main_url}/category/adventure"       : "Adventure",
        f"{main_url}/category/animation"       : "Animation",
        f"{main_url}/category/comedy"          : "Comedy",
        f"{main_url}/category/crime"           : "Crime",
        f"{main_url}/category/documentary"     : "Documentary",
        f"{main_url}/category/drama"           : "Drama",
        f"{main_url}/category/family"          : "Family",
        f"{main_url}/category/fantasy"         : "Fantasy",
        f"{main_url}/category/history"         : "History",
        f"{main_url}/category/horror"          : "Horror",
        f"{main_url}/category/kids"            : "Kids",
        f"{main_url}/category/music"           : "Music",
        f"{main_url}/category/mystery"         : "Mystery",
        f"{main_url}/category/news"            : "News",
        f"{main_url}/category/reality"         : "Reality",
        f"{main_url}/category/romance"         : "Romance",
        f"{main_url}/category/science-fiction" : "Science Fiction",
        f"{main_url}/category/soap"            : "Soap",
        f"{main_url}/category/talk"            : "Talk",
        f"{main_url}/category/thriller"        : "Thriller",
        f"{main_url}/category/tv-movie"        : "TV Movie",
        f"{main_url}/category/war"             : "War",
        f"{main_url}/category/western"         : "Western",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        target_url = f"{url}?page={page}" if page > 1 else url
        istek      = await self.async_cf_get(target_url)
        secici     = HTMLHelper(istek.text)

        results = []

        # Try Slides (Trending/Popular)
        for veri in secici.select("div.cb-slide"):
            title  = veri.select_text(".cb-slide-title") or veri.select_attr(".cb-slide-play", "data-title")
            href   = veri.select_attr("a.cb-btn-ghost-sm", "href") or veri.select_attr("a", "href")
            poster = veri.select_attr("div.cb-slide-bg", "style") or veri.select_attr("img", "src")
            if poster and "url" in poster:
                poster = re.search(r"url\(['\"]?(.+?)['\"]?\)", poster).group(1)

            if not href or not title:
                continue

            results.append(MainPageResult(
                category = category,
                title    = title,
                url      = self.fix_url(href),
                poster   = self.fix_url(poster)
            ))

        # Try Cards (Movies/TV/Categories)
        for veri in secici.select(".cb-card"):
            title  = veri.select_text(".cb-card-title") or veri.select_attr("img", "alt")
            href   = veri.select_attr("a", "href")
            poster = veri.select_attr("img", "src") or veri.select_attr("img", "data-src")

            if not href or not title:
                continue

            results.append(MainPageResult(
                category = category,
                title    = title,
                url      = self.fix_url(href),
                poster   = self.fix_url(poster)
            ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        link   = f"{self.main_url}/search?q={query}"
        istek  = await self.async_cf_get(link)
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.cb-card-grid div.cb-card"):
            title  = veri.select_text("h3.cb-card-title")
            href   = veri.select_attr("a", "href")
            poster = veri.select_attr("img", "src")

            results.append(SearchResult(
                title  = title,
                url    = self.fix_url(href),
                poster = self.fix_url(poster)
            ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        # Try to extract from LD+JSON first for robustness
        ld_json_raw = secici.regex_first(r'<script type="application/ld\+json">(.*?)</script>', flags=re.S)
        ld_data     = {}
        if ld_json_raw:
            try:
                ld_data = json.loads(ld_json_raw)
            except:
                pass

        title  = ld_data.get("name") or secici.select_attr("img.cb-detail-title-logo", "alt") or secici.select_text("h1")
        poster = ld_data.get("image") or secici.regex_first(r'"poster":"(.*?)"')
        desc   = ld_data.get("description") or secici.select_text("#cbPlot")

        # Meta info
        year   = ld_data.get("datePublished") or secici.regex_first(r'<span class="cb-meta-plain">(\d{4})</span>')
        rating = ld_data.get("aggregateRating", {}).get("ratingValue") or secici.regex_first(r'<i class="bi bi-star-fill".*?</i>\s*([\d\.]+)')

        # Genres
        tags = ld_data.get("genre")
        if not tags:
            tags = [a.text().strip() for a in secici.select("div.cb-detail-meta-row span.cb-meta-plain") if not re.match(r"^\d+h|\d{4}$", a.text().strip())]

        # Actors
        actors = [a.get("name") for a in ld_data.get("actor", []) if a.get("name")]
        if not actors:
             actors = [a.select_text(".cb-cast-item-name") for a in secici.select(".cb-cast-item-card")]

        # Determine if Movie or Series
        is_series = "/tv/" in url

        if is_series:
            episodes = []
            for season_div in secici.select("div.cb-season"):
                s_name = season_div.select_text("span.cb-season-number")
                s_num  = re.search(r"(\d+)", s_name).group(1) if re.search(r"(\d+)", s_name) else "1"

                for ep_a in season_div.select("a.cb-episode-item"):
                    ep_href  = ep_a.attrs.get("href")
                    ep_num   = ep_a.select_text("span.cb-episode-num")
                    ep_title = ep_a.select_text("div.cb-episode-title")

                    episodes.append(Episode(
                        season  = int(s_num),
                        episode = int(ep_num) if ep_num.isdigit() else 1,
                        title   = ep_title,
                        url     = self.fix_url(ep_href)
                    ))

            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = title,
                description = desc,
                tags        = tags,
                year        = year,
                rating      = rating,
                actors      = actors,
                episodes    = episodes
            )

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = desc,
            tags        = tags,
            year        = year,
            rating      = rating,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        embed_path = secici.select_attr("iframe#cbMoviePlayer", "data-src") or \
                    secici.select_attr("iframe", "data-src") or \
                    secici.regex_first(r"data-src=['\"](/embed/[^'\"]+)['\"]")

        if not embed_path:
            return []

        embed_url = self.fix_url(embed_path)

        # Now we need to go deeper into the embed to find the brightpathsignals link
        embed_istek  = await self.async_cf_get(embed_url, headers={"Referer": url})
        embed_secici = HTMLHelper(embed_istek.text)

        real_embed = embed_secici.select_attr("iframe#pf", "src") or \
                     embed_secici.regex_first(r"src=['\"](https?://brightpathsignals\.com/[^'\"]+)['\"]")

        if not real_embed:
            return []

        # Use the extractor
        results = []
        data    = await self.extract(real_embed, referer=embed_url)
        self.collect_results(results, data)

        return results
