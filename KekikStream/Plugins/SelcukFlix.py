# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode
from parsel           import Selector
import re, base64, json, urllib.parse

class SelcukFlix(PluginBase):
    name     = "SelcukFlix"
    main_url = "https://selcukflix.net"
    lang     = "tr"
    
    main_page = {
       "tum-bolumler" : "Yeni Eklenen Bölümler"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        full_url = f"{self.main_url}/{url}"
        resp = await self.cffi.get(full_url)
        sel = Selector(resp.text)
        
        results = []
        if "tum-bolumler" in url:
            for item in sel.css("div.col-span-3 a"):
                name = item.css("h2::text").get()
                ep_info = item.css("div.opacity-80::text").get()
                href = item.css("::attr(href)").get()
                poster = item.css("div.image img::attr(src)").get()
                
                if name and href:
                    title = f"{name} - {ep_info}" if ep_info else name
                    final_url = self.fix_url(href)
                    if "/dizi/" in final_url and "/sezon-" in final_url:
                        final_url = final_url.split("/sezon-")[0]
                    
                    results.append(MainPageResult(
                        category=category,
                        title=title,
                        url=final_url,
                        poster=self.fix_url(poster)
                    ))
        
        return results

    async def search(self, query: str) -> list[SearchResult]:
        search_url = f"{self.main_url}/api/bg/searchcontent?searchterm={query}"
        
        headers = {
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{self.main_url}/"
        }
        
        post_resp = await self.cffi.post(search_url, headers=headers)
        
        try:
            resp_json = post_resp.json()
            response_data = resp_json.get("response")
            
            raw_data = base64.b64decode(response_data)
            try:
                decoded_str = raw_data.decode('utf-8')
            except UnicodeDecodeError:
                decoded_str = raw_data.decode('iso-8859-1').encode('utf-8').decode('utf-8')
                
            search_data = json.loads(decoded_str)
            
            results = []
            for item in search_data.get("result", []):
                title = item.get("title")
                slug  = item.get("slug")
                poster = item.get("poster")
                if poster:
                    poster = self.clean_image_url(poster)
                
                if slug and "/seri-filmler/" not in slug:
                    results.append(SearchResult(
                        title=title,
                        url=self.fix_url(slug),
                        poster=poster
                    ))
            return results
            
        except Exception:
            return []

    async def load_item(self, url: str) -> SeriesInfo:
        resp = await self.cffi.get(url)
        sel  = Selector(resp.text)
        
        next_data = sel.css("script#__NEXT_DATA__::text").get()
        if not next_data: 
             return None
        
        data = json.loads(next_data)
        secure_data = data["props"]["pageProps"]["secureData"]
        raw_data = base64.b64decode(secure_data.replace('"', ''))
        try:
            decoded_str = raw_data.decode('utf-8')
        except UnicodeDecodeError:
            decoded_str = raw_data.decode('iso-8859-1') # .encode('utf-8').decode('utf-8') implied
        
        content_details = json.loads(decoded_str)
        item = content_details.get("contentItem", {})
            
        title = item.get("original_title") or item.get("originalTitle")
        poster = self.clean_image_url(item.get("poster_url") or item.get("posterUrl"))
        description = item.get("description") or item.get("used_description")
        rating = str(item.get("imdb_point") or item.get("imdbPoint", ""))
        
        series_data = content_details.get("relatedData", {}).get("seriesData")
        if not series_data and "RelatedResults" in content_details:
             series_data = content_details["RelatedResults"].get("getSerieSeasonAndEpisodes", {}).get("result")
             if series_data and isinstance(series_data, list):
                  pass

        episodes = []
        if series_data:
             seasons_list = []
             if isinstance(series_data, dict):
                 seasons_list = series_data.get("seasons", [])
             elif isinstance(series_data, list):
                 seasons_list = series_data

             for season in seasons_list:
                if not isinstance(season, dict): continue
                s_no = season.get("season_no") or season.get("seasonNo") # Try snake_case too
                ep_list = season.get("episodes", [])
                for ep in ep_list:
                    episodes.append(Episode(
                        season = s_no,
                        episode = ep.get("episode_no") or ep.get("episodeNo"),
                        title = ep.get("ep_text") or ep.get("epText"),
                        url = self.fix_url(ep.get("used_slug") or ep.get("usedSlug"))
                    ))
        
        return SeriesInfo(
            title=title,
            url=url,
            poster=poster,
            description=description,
            rating=rating,
            episodes=episodes
        )

    async def load_links(self, url: str) -> list[dict]:
        resp = await self.cffi.get(url)
        sel  = Selector(resp.text)
        
        next_data = sel.css("script#__NEXT_DATA__::text").get()
        if not next_data: return []

        try:
             data = json.loads(next_data)
             secure_data = data["props"]["pageProps"]["secureData"]
             raw_data = base64.b64decode(secure_data.replace('"', ''))
             try:
                 decoded_str = raw_data.decode('utf-8')
             except UnicodeDecodeError:
                 decoded_str = raw_data.decode('iso-8859-1')
            
             content_details = json.loads(decoded_str)
             related_data = content_details.get("relatedData", {})
             
             source_content = None
             
             # Check if Series (episode) or Movie
             if "/dizi/" in url:
                 if related_data.get("episodeSources", {}).get("state"):
                      res = related_data["episodeSources"].get("result", [])
                      if res:
                          source_content = res[0].get("sourceContent")
             else:
                 # Movie
                 if related_data.get("movieParts", {}).get("state"):
                      # Looking for first part source
                      movie_parts = related_data["movieParts"].get("result", [])
                      if movie_parts:
                          first_part_id = movie_parts[0].get("id")
                          # RelatedResults -> getMoviePartSourcesById_ID
                          rr = content_details.get("RelatedResults", {})
                          key = f"getMoviePartSourcesById_{first_part_id}"
                          if key in rr:
                              res = rr[key].get("result", [])
                              if res:
                                  source_content = res[0].get("source_content")

             results = []
             if source_content:
                 iframe_sel = Selector(source_content)
                 iframe_src = iframe_sel.css("iframe::attr(src)").get()
                 if iframe_src:
                     iframe_src = self.fix_url(iframe_src)
                     # Domain replace
                     if "sn.dplayer74.site" in iframe_src:
                         iframe_src = iframe_src.replace("sn.dplayer74.site", "sn.hotlinger.com")
                     
                     extractor = self.ex_manager.find_extractor(iframe_src)
                     results.append({
                         "url": iframe_src,
                         "name": extractor.name if extractor else "Iframe"
                     })
             
             return results

        except Exception:
            return []

    def clean_image_url(self, url: str) -> str:
        if not url: return None
        url = url.replace("images-macellan-online.cdn.ampproject.org/i/s/", "")
        url = url.replace("file.dizilla.club", "file.macellan.online")
        url = url.replace("images.dizilla.club", "images.macellan.online")
        url = url.replace("images.dizimia4.com", "images.macellan.online")
        url = url.replace("file.dizimia4.com", "file.macellan.online")
        url = url.replace("/f/f/", "/630/910/")
        return self.fix_url(url)
