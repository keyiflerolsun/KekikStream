# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
from json             import dumps, loads
import re

class Watch32(PluginBase):
    name        = "Watch32"
    language    = "en"
    main_url    = "https://watch32.sx"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64" 
    description = "Watch Your Favorite Movies &amp; TV Shows Online - Streaming For Free. With Movies &amp; TV Shows Full HD. Find Your Movies &amp; Watch NOW!"

    main_page = {
        # Main Categories
        f"{main_url}/movie?page="           : "Popular Movies",
        f"{main_url}/tv-show?page="         : "Popular TV Shows",
        f"{main_url}/coming-soon?page="     : "Coming Soon",
        f"{main_url}/top-imdb?page="        : "Top IMDB Rating",
        # Genre Categories
        f"{main_url}/genre/action?page="    : "Action",
        f"{main_url}/genre/adventure?page=" : "Adventure",
        f"{main_url}/genre/animation?page=" : "Animation",
        f"{main_url}/genre/biography?page=" : "Biography",
        f"{main_url}/genre/comedy?page="    : "Comedy",
        f"{main_url}/genre/crime?page="     : "Crime",
        f"{main_url}/genre/documentary?page=" : "Documentary",
        f"{main_url}/genre/drama?page="     : "Drama",
        f"{main_url}/genre/family?page="    : "Family",
        f"{main_url}/genre/fantasy?page="   : "Fantasy",
        f"{main_url}/genre/history?page="   : "History",
        f"{main_url}/genre/horror?page="    : "Horror",
        f"{main_url}/genre/music?page="     : "Music",
        f"{main_url}/genre/mystery?page="   : "Mystery",
        f"{main_url}/genre/romance?page="   : "Romance",
        f"{main_url}/genre/science-fiction?page=" : "Science Fiction",
        f"{main_url}/genre/thriller?page="  : "Thriller",
        f"{main_url}/genre/war?page="       : "War",
        f"{main_url}/genre/western?page="   : "Western",
    }


    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}{page}")
        helper = HTMLHelper(istek.text)
        items  = helper.select("div.flw-item")

        return [
            MainPageResult(
                category = category,
                title    = helper.select_attr("h2.film-name a", "title", veri),
                url      = self.fix_url(helper.select_attr("h2.film-name a", "href", veri)),
                poster   = helper.select_attr("img.film-poster-img", "data-src", veri)
            )
            for veri in items
        ]

    async def search(self, query: str) -> list[SearchResult]:
        slug = query.replace(" ", "-")
        url  = f"{self.main_url}/search/{slug}"
        
        istek  = await self.httpx.get(url)
        helper = HTMLHelper(istek.text)
        items  = helper.select("div.flw-item")

        return [
            SearchResult(
                title  = helper.select_attr("h2.film-name a", "title", veri),
                url    = self.fix_url(helper.select_attr("h2.film-name a", "href", veri)),
                poster = helper.select_attr("img.film-poster-img", "data-src", veri)
            )
            for veri in items
        ]

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        helper = HTMLHelper(istek.text)
        
        content_id = helper.select_attr("div.detail_page-watch", "data-id")
        details    = helper.select_first("div.detail_page-infor")
        name       = helper.select_text("h2.heading-name > a", details)
        
        poster      = helper.select_attr("div.film-poster > img", "src", details)
        description = helper.select_text("div.description", details)
        
        # Release year extraction
        year_text = helper.regex_first(r"Released:\s*(\d{4})")
        if not year_text:
             # Fallback for series
             year_text = helper.regex_first(r"Released:.+?(\d{4})")
        
        # Tags/Genres
        tags = helper.select_all_text("div.row-line:has(> span.type > strong:contains(Genre)) a")
        
        # Rating
        rating = helper.select_text("button.btn-imdb")
        if rating:
            rating = rating.replace("N/A", "").split(":")[-1].strip()

        # Actors
        actors = helper.select_all_text("div.row-line:has(> span.type > strong:contains(Casts)) a")

        if "movie" in url:
            return MovieInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = name,
                description = description,
                tags        = tags,
                rating      = rating,
                year        = year_text,
                actors      = actors
            )
        else:
            episodes = []
            seasons_resp = await self.httpx.get(f"{self.main_url}/ajax/season/list/{content_id}")
            sh = HTMLHelper(seasons_resp.text)
            seasons = sh.select("a.dropdown-item") # Relaxed selector from a.ss-item
            
            for season in seasons:
                season_id = season.attrs.get("data-id")
                season_num_text = season.text().replace("Season ", "").replace("Series", "").strip()
                season_num = int(season_num_text) if season_num_text.isdigit() else 1
                
                episodes_resp = await self.httpx.get(f"{self.main_url}/ajax/season/episodes/{season_id}")
                eh = HTMLHelper(episodes_resp.text)
                eps = eh.select("a.eps-item")
                
                for ep in eps:
                    ep_id = ep.attrs.get("data-id")
                    ep_title_raw = ep.attrs.get("title", "")
                    # Eps 1: Name
                    m = re.search(r"Eps (\d+): (.+)", ep_title_raw)
                    if m:
                        ep_num  = int(m.group(1))
                        ep_name = m.group(2)
                    else:
                        ep_num  = 1
                        ep_name = ep_title_raw
                        
                    episodes.append(Episode(
                        season  = season_num,
                        episode = ep_num,
                        title   = ep_name,
                        url     = f"servers/{ep_id}"
                    ))
            
            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = name,
                description = description,
                tags        = tags,
                rating      = rating,
                year        = year_text,
                actors      = actors,
                episodes    = episodes
            )

    async def load_links(self, url: str) -> list[ExtractResult]:
        # url in load_links might be the full page URL for movies or "servers/epId" for episodes
        if "servers/" in url:
            data = url.split("/")[-1]
        if "servers/" in url:
            data = url.split("/")[-1]
            servers_url = f"servers/{data}"
        elif "list/" in url:
            data = url.split("/")[-1]
            servers_url = f"list/{data}"
        else:
             # Re-fetch page to get contentId only if we don't have list/ or servers/
             istek = await self.httpx.get(url)
             helper = HTMLHelper(istek.text)
             content_id = helper.select_attr("div.detail_page-watch", "data-id")
             if not content_id:
                # Try to get id from url if direct parse fails, similar to Kotlin logic
                # But Kotlin parses search first. Here we assume we are at the page.
                # If no content_id found, maybe it's not a valid page or structure changed.
                return []
             servers_url = f"list/{content_id}"

        servers_resp = await self.httpx.get(f"{self.main_url}/ajax/episode/{servers_url}")
        sh = HTMLHelper(servers_resp.text)
        servers = sh.select("a.link-item")
        
        results = []
        for server in servers:
            link_id = server.attrs.get("data-linkid") or server.attrs.get("data-id")
            source_resp = await self.httpx.get(f"{self.main_url}/ajax/episode/sources/{link_id}")
            source_data = source_resp.json()
            video_url = source_data.get("link")
            
            if video_url:
                # Use extractors if possible
                extract_result = await self.extract(video_url)
                if extract_result:
                    if isinstance(extract_result, list):
                        results.extend(extract_result)
                    else:
                        results.append(extract_result)
                else:
                    results.append(ExtractResult(
                        url  = video_url,
                        name = f"{self.name} | {server.text()}"
                    ))
                    
        return results
