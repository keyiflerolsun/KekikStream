# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, MovieInfo, ExtractResult
from parsel           import Selector
import re, json, urllib.parse

class Sinefy(PluginBase):
    name        = "Sinefy"
    language    = "tr"
    main_url    = "https://sinefy3.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Yabancı film izle olarak vizyondaki en yeni yabancı filmleri türkçe dublaj ve altyazılı olarak en hızlı şekilde full hd olarak sizlere sunuyoruz."

    main_page = {
        f"{main_url}/page/"                      : "Son Eklenenler",
        f"{main_url}/en-yenifilmler"             : "Yeni Filmler",
        f"{main_url}/netflix-filmleri-izle"      : "Netflix Filmleri",
        f"{main_url}/dizi-izle/netflix"          : "Netflix Dizileri",
        f"{main_url}/gozat/filmler/animasyon" 	 : "Animasyon",
        f"{main_url}/gozat/filmler/komedi" 		 : "Komedi",
        f"{main_url}/gozat/filmler/suc" 		 : "Suç",
        f"{main_url}/gozat/filmler/aile" 		 : "Aile",
        f"{main_url}/gozat/filmler/aksiyon" 	 : "Aksiyon",
        f"{main_url}/gozat/filmler/macera" 		 : "Macera",
        f"{main_url}/gozat/filmler/fantastik" 	 : "Fantastik",
        f"{main_url}/gozat/filmler/korku" 		 : "Korku",
        f"{main_url}/gozat/filmler/romantik" 	 : "Romantik",
        f"{main_url}/gozat/filmler/savas" 		 : "Savaş",
        f"{main_url}/gozat/filmler/gerilim" 	 : "Gerilim",
        f"{main_url}/gozat/filmler/bilim-kurgu"  : "Bilim Kurgu",
        f"{main_url}/gozat/filmler/dram" 		 : "Dram",
        f"{main_url}/gozat/filmler/gizem" 		 : "Gizem",
        f"{main_url}/gozat/filmler/western" 	 : "Western",
        f"{main_url}/gozat/filmler/ulke/turkiye" : "Türk Filmleri",
        f"{main_url}/gozat/filmler/ulke/kore"    : "Kore Filmleri"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        if "page/" in url:
             full_url = f"{url}{page}"
        elif "en-yenifilmler" in url or "netflix" in url:
             full_url = f"{url}/{page}"
        else:
             full_url = f"{url}&page={page}"

        resp = await self.httpx.get(full_url)
        sel  = Selector(resp.text)

        results = []
        # Kotlin: div.poster-with-subject, div.dark-segment div.poster-md.poster
        for item in sel.css("div.poster-with-subject, div.dark-segment div.poster-md.poster"):
             title  = item.css("h2::text").get()
             href   = item.css("a::attr(href)").get()
             poster = item.css("img::attr(data-srcset)").get()
             if poster:
                  poster = poster.split(",")[0].split(" ")[0]

             if title and href:
                 results.append(MainPageResult(
                     category = category,
                     title    = title,
                     url      = self.fix_url(href),
                     poster   = self.fix_url(poster)
                 ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        # Try to get dynamic keys from main page first
        c_key   = "ca1d4a53d0f4761a949b85e51e18f096"
        c_value = "MTc0NzI2OTAwMDU3ZTEwYmZjMDViNWFmOWIwZDViODg0MjU4MjA1ZmYxOThmZTYwMDdjMWQzMzliNzY5NzFlZmViMzRhMGVmNjgwODU3MGIyZA=="

        try:
             resp = await self.httpx.get(self.main_url)
             sel  = Selector(resp.text)
             cke  = sel.css("input[name='cKey']::attr(value)").get()
             cval = sel.css("input[name='cValue']::attr(value)").get()
             if cke and cval:
                 c_key   = cke
                 c_value = cval

        except Exception:
            pass

        post_url = f"{self.main_url}/bg/searchcontent"
        data = {
            "cKey"       : c_key,
            "cValue"     : c_value,
            "searchTerm" : query
        }
        
        headers = {
            "User-Agent"       : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
            "Accept"           : "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With" : "XMLHttpRequest",
            "Content-Type"     : "application/x-www-form-urlencoded; charset=UTF-8"
        }
        
        response = await self.httpx.post(post_url, data=data, headers=headers)
        
        try:
            # Extract JSON data from response (might contain garbage chars at start)
            raw = response.text
            json_start = raw.find('{')
            if json_start != -1:
                clean_json = raw[json_start:]
                data = json.loads(clean_json)
                
                results = []
                # Result array is in data['data']['result']
                res_array = data.get("data", {}).get("result", [])
                
                if not res_array:
                     # Fallback manual parsing ?
                     pass

                for item in res_array:
                     name = item.get("object_name")
                     slug = item.get("used_slug")
                     poster = item.get("object_poster_url")
                     
                     if name and slug:
                         if "cdn.ampproject.org" in poster:
                              poster = "https://images.macellan.online/images/movie/poster/180/275/80/" + poster.split("/")[-1]
                         
                         results.append(SearchResult(
                             title=name,
                             url=self.fix_url(slug),
                             poster=self.fix_url(poster)
                         ))
                return results

        except Exception:
            pass
        return []

    async def load_item(self, url: str) -> SeriesInfo:
        resp = await self.httpx.get(url)
        sel  = Selector(resp.text)
        
        title       = sel.css("h1::text").get()
        poster_info = sel.css("div.ui.items img::attr(data-srcset)").get()
        poster      = None
        if poster_info:
             # take 1x
             parts = str(poster_info).split(",")
             for p in parts:
                 if "1x" in p:
                     poster = p.strip().split(" ")[0]
                     break
        
        description = sel.css("p#tv-series-desc::text").get()
        tags        = sel.css("div.item.categories a::text").getall()
        rating      = sel.css("span.color-imdb::text").get()
        actors      = sel.css("div.content h5::text").getall()
        year        = sel.css("span.item.year::text").get()  # Year bilgisi eklendi
        
        episodes = []
        season_elements = sel.css("section.episodes-box")
        
        if season_elements:
             # Get season links
             season_links = []
             menu = sel.css("div.ui.vertical.fluid.tabular.menu a")
             for link in menu:
                 href = link.css("::attr(href)").get()
                 if href:
                     season_links.append(self.fix_url(href))
             
             for s_url in season_links:
                 target_url = s_url if "/bolum-" in s_url else f"{s_url}/bolum-1"
                 
                 try:
                     s_resp = await self.httpx.get(target_url)
                     s_sel  = Selector(s_resp.text)
                     ep_links = s_sel.css("div.ui.list.celled a.item")
                     
                     current_season_no = 1
                     match = re.search(r"sezon-(\d+)", target_url)
                     if match:
                         current_season_no = int(match.group(1))
                     
                     for ep_link in ep_links:
                         href = ep_link.css("::attr(href)").get()
                         name = ep_link.css("div.content div.header::text").get()
                         
                         if href:
                             ep_no = 0
                             match_ep = re.search(r"bolum-(\d+)", href)
                             if match_ep:
                                 ep_no = int(match_ep.group(1))
                                 
                             episodes.append(Episode(
                                 season = current_season_no,
                                 episode = ep_no,
                                 title = name.strip() if name else "",
                                 url = self.fix_url(href)
                             ))
                 except Exception:
                     pass
        
        if episodes:
            return SeriesInfo(
                title    = title,
                url      = url,
                poster   = self.fix_url(poster),
                description = description,
                rating   = rating,
                tags     = tags,
                actors   = actors,
                year     = year,
                episodes = episodes
            )
        else:
            return MovieInfo(
                title       = title,
                url         = url,
                poster      = self.fix_url(poster),
                description = description,
                rating      = rating,
                tags        = tags,
                actors      = actors,
                year        = year
            )

    async def load_links(self, url: str) -> list[ExtractResult]:
        resp = await self.httpx.get(url)
        sel  = Selector(resp.text)
        
        iframe = sel.css("iframe::attr(src)").get()
        if not iframe:
            return []
            
        iframe_url = self.fix_url(iframe)
        
        # Always return iframe (matching Kotlin - no extractor check)
        # loadExtractor in Kotlin handles extraction internally
        return [ExtractResult(
            url  = iframe_url,
            name = "Sinefy Player"
        )]
