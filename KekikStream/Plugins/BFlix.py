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
        f"{main_url}/movies?page="       : "Movies",
        f"{main_url}/tv-series?page="    : "TV Shows",
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

        title       = secici.select_text("h1.film-title") or secici.select_text("h1") or secici.meta_value("og:title")
        img_el      = secici.select_first("div.film-poster img")
        poster      = img_el.select_attr(None, "src") if img_el else None
        poster      = poster or secici.meta_value("og:image")
        description = secici.select_text("div.film-desc") or secici.meta_value("og:description")

        meta_rows = secici.select("div.film-meta > div")
        year      = None
        rating    = None
        tags      = []
        actors    = []
        duration  = None

        subtitle_div = secici.select_first("div.film-subtitle")
        if subtitle_div:
            for span in subtitle_div.select("span"):
                span_text = span.text(strip=True)
                if "min" in span_text:
                    try:
                        duration = int(span_text.replace("min", "").strip())
                    except:
                        pass
                elif span.attrs.get("class") == ["rating"]:
                    rating = span_text
                elif span.select_first("i.fa-star"):
                    # rating fallback or user score
                    pass

        for row in meta_rows:
            label_div = row.select_first("div > div")
            if label_div:
                label    = label_div.text(strip=True).replace(":", "").strip()
                val_span = row.select_first("span")
                if val_span:
                    if label == "Year":
                        year = val_span.text(strip=True)
                    elif label == "Genre":
                        tags = [a.text(strip=True) for a in val_span.select("a")]
                    elif label == "Cast":
                        actors = [a.text(strip=True) for a in val_span.select("a")]

        is_series = "/tv/" in url or "/series/" in url
        if is_series:
            episodes = []
            # Find current season AJAX URL
            ajax_url = secici.regex_first(r"const current_url = '([^']+)'")
            if ajax_url:
                ajax_istek  = await self.async_cf_get(ajax_url, headers={"Referer": url})
                ajax_secici = HTMLHelper(ajax_istek.text)
                for li in ajax_secici.select("li"):
                    a_tag = li.select_first("a")
                    if a_tag:
                        ep_href = a_tag.attrs.get("href")
                        ep_name = a_tag.text(strip=True)

                        s, e = None, None
                        if ep_href:
                            # Path is like /series/show-name/1-1/
                            match = re.search(r'/(\d+)-(\d+)/?$', ep_href)
                            if match:
                                s = int(match.group(1))
                                e = int(match.group(2))

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
                description = description.strip() if description else "",
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
            description = description.strip() if description else "",
            tags        = tags,
            year        = year,
            rating      = rating,
            actors      = actors,
            duration    = duration
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        # Retrieve player servers list via pl_url AJAX
        pl_url   = secici.regex_first(r"const pl_url = '([^']+)'")
        response = []

        if pl_url:
            ajax_resp = await self.async_cf_get(pl_url, headers={"Referer": url})
            if ajax_resp.status_code == 200:
                ajax_secici = HTMLHelper(ajax_resp.text)
                for server in ajax_secici.select("div.film-server, div.sv-item"):
                    player_url  = server.attrs.get("data-id")
                    server_name = server.attrs.get("data-srv") or "Server"
                    if player_url:
                        # Extract the stream using the selected player URL
                        data = await self.extract(self.fix_url(player_url), referer=url)
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
                                url        = self.fix_url(player_url),
                                name       = f"{server_name}",
                                referer    = url,
                                user_agent = self.httpx.headers.get("User-Agent")
                            ))

        # Fallback to direct iframe parsing if no AJAX URL is found
        if not response:
            for iframe in secici.select("iframe"):
                src = iframe.attrs.get("src")
                if src:
                    data = await self.extract(self.fix_url(src), referer=url)
                    if data:
                        if isinstance(data, list):
                            for item in data:
                                item.name       = "Iframe"
                                item.referer    = url
                                item.user_agent = self.httpx.headers.get("User-Agent")
                        else:
                            data.name       = "Iframe"
                            data.referer    = url
                            data.user_agent = self.httpx.headers.get("User-Agent")
                        self.collect_results(response, data)
                    else:
                        response.append(ExtractResult(
                            url        = self.fix_url(src),
                            name       = "Iframe",
                            referer    = url,
                            user_agent = self.httpx.headers.get("User-Agent")
                        ))

        return response
