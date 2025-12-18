# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, MovieInfo
from parsel           import Selector
import re, base64, json, urllib.parse

class RoketDizi(PluginBase):
    name        = "RoketDizi"
    lang        = "tr"
    main_url    = "https://roketdizi.to"

    # Domain doğrulama ve anti-bot mekanizmaları var
    requires_cffi = True

    main_page = {
       "dizi/tur/aksiyon"     : "Aksiyon",
       "dizi/tur/bilim-kurgu" : "Bilim Kurgu",
       "dizi/tur/gerilim"     : "Gerilim",
       "dizi/tur/fantastik"   : "Fantastik",
       "dizi/tur/komedi"      : "Komedi",
       "dizi/tur/korku"       : "Korku",
       "dizi/tur/macera"      : "Macera",
       "dizi/tur/suc"         : "Suç"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        full_url = f"{self.main_url}/{url}?&page={page}"
        resp     = await self.cffi.get(full_url)
        sel      = Selector(resp.text)

        results = []

        for item in sel.css("div.w-full.p-4 span.bg-\\[\\#232323\\]"):
             title  = item.css("span.font-normal.line-clamp-1::text").get()
             href   = item.css("a::attr(href)").get()
             poster = item.css("img::attr(src)").get()
             
             if title and href:
                 results.append(MainPageResult(
                     category = category,
                     title    = title,
                     url      = self.fix_url(href),
                     poster   = self.fix_url(poster)
                 ))
        return results

    async def search(self, query: str) -> list[SearchResult]:
        # Get Cookies and Keys
        main_req = await self.cffi.get(self.main_url)
        sel = Selector(main_req.text)
        
        c_key   = sel.css("input[name='cKey']::attr(value)").get()
        c_value = sel.css("input[name='cValue']::attr(value)").get()
        
        post_url = f"{self.main_url}/api/bg/searchContent?searchterm={query}"
        
        headers = {
            "Accept"           : "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With" : "XMLHttpRequest",
            "Referer"          : f"{self.main_url}/",
            "CNT"              : "vakTR"
        }

        data = {}
        if c_key and c_value:
            data = {"cKey": c_key, "cValue": c_value}
        
        search_req = await self.cffi.post(post_url, data=data, headers=headers)
        
        try:
            resp_json = search_req.json()
            if not resp_json.get("state"):
                return []
            
            html_content = resp_json.get("html", "").strip()
            sel_results = Selector(html_content)

            results = []
            items = re.findall(r'<a href="([^"]+)".*?data-srcset="([^"]+).*?<span class="text-white">([^<]+)', html_content, re.DOTALL)
            
            for href, poster, title in items:
                 results.append(SearchResult(
                     title  = title.strip(),
                     url    = self.fix_url(href.strip()),
                     poster = self.fix_url(poster.strip())
                 ))
            
            return results

        except Exception:
            return []

    async def load_item(self, url: str) -> SeriesInfo:
        # Note: Handling both Movie and Series logic in one, returning SeriesInfo generally or MovieInfo
        resp = await self.cffi.get(url)
        sel  = Selector(resp.text)
        
        title       = sel.css("h1.text-white::text").get()
        poster      = sel.css("div.w-full.page-top img::attr(src)").get()
        description = sel.css("div.mt-2.text-sm::text").get()
        
        year = None # Implement if critical
        
        tags = sel.css("h3.text-white.opacity-60::text").get()
        if tags:
            tags = [t.strip() for t in tags.split(",")]
            
        rating = sel.css("div.flex.items-center span.text-white.text-sm::text").get()
        actors = sel.css("div.global-box h5::text").getall()

        # Check urls for episodes
        all_urls = re.findall(r'"url":"([^"]*)"', resp.text)
        is_series = any("bolum-" in u for u in all_urls)
        
        episodes = []
        if is_series:
            seen_eps = set()
            for u in all_urls:
                if "bolum" in u and u not in seen_eps:
                    seen_eps.add(u)
                    season_match = re.search(r'/sezon-(\d+)', u)
                    ep_match     = re.search(r'/bolum-(\d+)', u)
                    
                    season = int(season_match.group(1)) if season_match else 1
                    episode_num = int(ep_match.group(1)) if ep_match else 1
                    
                    episodes.append(Episode(
                        season  = season,
                        episode = episode_num,
                        title   = f"{season}. Sezon {episode_num}. Bölüm", # Placeholder title
                        url     = self.fix_url(u)
                    ))
        
        return SeriesInfo(
            title       = title,
            url         = url,
            poster      = self.fix_url(poster),
            description = description,
            tags        = tags,
            rating      = rating,
            actors      = actors,
            episodes    = episodes,
            year        = year
        )

    async def load_links(self, url: str) -> list[dict]:
        resp = await self.cffi.get(url)
        sel  = Selector(resp.text)
        
        next_data = sel.css("script#__NEXT_DATA__::text").get()
        if not next_data:
            return []
            
        try:
            data = json.loads(next_data)
            secure_data = data["props"]["pageProps"]["secureData"]
            decoded = base64.b64decode(secure_data).decode('utf-8')
            
            results = []
            matches = re.findall(r'iframe src=\\"([^"]*)\\"', decoded)
            for m in matches:
                iframe_url = m.replace('\\', '')
                if "http" not in iframe_url:
                     if iframe_url.startswith("//"):
                         iframe_url = "https:" + iframe_url
                     else:
                         iframe_url = "https://" + iframe_url # fallback
                
                # Check extractor
                extractor = self.ex_manager.find_extractor(iframe_url)
                name = extractor.name if extractor else "Iframe"
                
                results.append({
                    "url": iframe_url,
                    "name": name
                })
            
            return results

        except Exception:
            return []
