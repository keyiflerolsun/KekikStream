# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo
from parsel           import Selector
import re, base64

class Sinezy(PluginBase):
    name     = "Sinezy"
    main_url = "https://sinezy.site"
    lang     = "tr"
    
    main_page = {
       "izle/en-yeni-filmler/" : "Yeni Filmler",
       "izle/en-yi-filmler/"  : "En İyi Filmler"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        full_url = f"{self.main_url}/{url}page/{page}/"
        resp = await self.cffi.get(full_url)
        sel = Selector(resp.text)
        
        results = []
        for item in sel.css("div.container div.content div.movie_box.move_k"):
             title = item.css("a::attr(title)").get()
             href  = item.css("a::attr(href)").get()
             poster= item.css("img::attr(data-src)").get()
             
             if title and href:
                 results.append(MainPageResult(
                     category=category,
                     title=title,
                     url=self.fix_url(href),
                     poster=self.fix_url(poster)
                 ))
        return results

    async def search(self, query: str) -> list[SearchResult]:
        url = f"{self.main_url}/arama/?s={query}"
        resp = await self.cffi.get(url)
        sel = Selector(resp.text)
        
        results = []
        for item in sel.css("div.movie_box.move_k"):
             title = item.css("a::attr(title)").get()
             href  = item.css("a::attr(href)").get()
             poster= item.css("img::attr(data-src)").get()
             
             if title and href:
                 results.append(SearchResult(
                     title=title,
                     url=self.fix_url(href),
                     poster=self.fix_url(poster)
                 ))
        return results

    async def load_item(self, url: str) -> MovieInfo:
        resp = await self.cffi.get(url)
        sel  = Selector(resp.text)
        
        title       = sel.css("div.detail::attr(title)").get()
        poster      = sel.css("div.move_k img::attr(data-src)").get()
        description = sel.css("div.desc.yeniscroll p::text").get()
        rating      = sel.css("span.info span.imdb::text").get()
        
        tags = sel.css("div.detail span a::text").getall()
        actors = sel.css("span.oyn p::text").getall() # Might need splitting logic
        
        return MovieInfo(
            title=title,
            url=url,
            poster=self.fix_url(poster),
            description=description,
            tags=tags,
            rating=rating,
            actors=actors
        )

    async def load_links(self, url: str) -> list[dict]:
        resp = await self.cffi.get(url)
        
        match = re.search(r"ilkpartkod\s*=\s*'([^']+)'", resp.text, re.IGNORECASE)
        if match:
             encoded = match.group(1)
             try:
                 decoded = base64.b64decode(encoded).decode('utf-8')
                 iframe_match = re.search(r'src="([^"]*)"', decoded)
                 if iframe_match:
                     iframe = iframe_match.group(1)
                     iframe = self.fix_url(iframe)
                     
                     extractor = self.ex_manager.find_extractor(iframe)
                     return [{
                         "url": iframe,
                         "name": extractor.name if extractor else "Iframe"
                     }]
             except Exception:
                 pass
        
        return []
