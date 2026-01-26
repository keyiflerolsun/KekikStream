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
        
        content_id  = helper.select_attr("div.detail_page-watch", "data-id")
        details     = helper.select_first("div.detail_page-infor")
        name        = helper.select_text("h2.heading-name > a", details)
        poster      = helper.select_poster("div.film-poster > img", details)
        description = helper.select_text("div.description", details)
        year        = str(helper.extract_year())
        tags        = helper.meta_list("Genre", container_selector="div.row-line")
        rating      = helper.select_text("button.btn-imdb").replace("N/A", "").split(":")[-1].strip() if helper.select_text("button.btn-imdb") else None
        actors      = helper.meta_list("Casts", container_selector="div.row-line")

        common_info = {
            "url"         : url,
            "poster"      : self.fix_url(poster),
            "title"       : name or "Bilinmiyor",
            "description" : description,
            "tags"        : tags,
            "rating"      : rating,
            "year"        : year,
            "actors"      : actors
        }

        if "movie" in url:
            return MovieInfo(**common_info)
        
        episodes = []
        seasons_resp = await self.httpx.get(f"{self.main_url}/ajax/season/list/{content_id}")
        sh = HTMLHelper(seasons_resp.text)
        
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
