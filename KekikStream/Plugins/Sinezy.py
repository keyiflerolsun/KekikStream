# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo
from parsel           import Selector
import re, base64

class Sinezy(PluginBase):
    name        = "Sinezy"
    language    = "tr"
    main_url    = "https://sinezy.fit"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Yerli ve yabancı film izle! Türkçe Dublaj ve Alt Yazılı Seçenekleriyle full hd film izlemek için En çok tercih edilen adres!"

    main_page = {
        f"{main_url}/izle/en-yeni-filmler/"        : "Yeni Filmler",
        f"{main_url}/izle/en-yi-filmler/"          : "En İyi Filmler",
        f"{main_url}/izle/aksiyon-filmleri/"       : "Aksiyon ",
        f"{main_url}/izle/animasyon-filmleri/"     : "Animasyon",
        f"{main_url}/izle/belgesel-izle/"          : "Belgesel",
        f"{main_url}/izle/bilim-kurgu-filmleri/"   : "Bilim Kurgu ",
        f"{main_url}/izle/biyografi-filmleri/"     : "Biyografi ",
        f"{main_url}/izle/dram-filmleri/"          : "Dram",
        f"{main_url}/izle/erotik-film-izle/"       : "Erotik ",
        f"{main_url}/izle/fantastik-filmler/"      : "Fantastik",
        f"{main_url}/izle/gelecek-filmler/"        : "Yakında",
        f"{main_url}/izle/gerilim-filmleri/"       : "Gerilim ",
        f"{main_url}/izle/gizem-filmleri/"         : "Gizem ",
        f"{main_url}/izle/komedi-filmleri/"        : "Komedi ",
        f"{main_url}/izle/korku-filmleri/"         : "Korku ",
        f"{main_url}/izle/macera-filmleri/"        : "Macera ",
        f"{main_url}/izle/muzikal-izle/"           : "Müzikal",
        f"{main_url}/izle/romantik-film/"          : "Romantik ",
        f"{main_url}/izle/savas-filmleri/"         : "Savaş ",
        f"{main_url}/izle/spor-filmleri/"          : "Spor ",
        f"{main_url}/izle/suc-filmleri/"           : "Suç ",
        f"{main_url}/izle/tarih-filmleri/"         : "Tarih ",
        f"{main_url}/izle/turkce-altyazili-promo/" : "Altyazılı Pro",
        f"{main_url}/izle/yabanci-dizi/"           : "Yabancı Dizi",
        f"{main_url}/izle/en-iyi-filmler/"         : "En İyi Filmler",
        f"{main_url}/izle/en-yeni-filmler/"        : "Yeni Filmler",
        f"{main_url}/izle/yerli-filmler/"          : "Yerli Filmler",
        f"{main_url}/izle/yetiskin-film/"          : "Yetişkin +18",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        full_url = f"{url}page/{page}/"
        resp     = await self.httpx.get(full_url)
        sel      = Selector(resp.text)
        
        results = []
        for item in sel.css("div.container div.content div.movie_box.move_k"):
             title  = item.css("a::attr(title)").get()
             href   = item.css("a::attr(href)").get()
             poster = item.css("img::attr(data-src)").get()
             
             if title and href:
                 results.append(MainPageResult(
                     category = category,
                     title    = title,
                     url      = self.fix_url(href),
                     poster   = self.fix_url(poster)
                 ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        url  = f"{self.main_url}/arama/?s={query}"
        resp = await self.httpx.get(url)
        sel  = Selector(resp.text)

        results = []
        for item in sel.css("div.movie_box.move_k"):
             title  = item.css("a::attr(title)").get()
             href   = item.css("a::attr(href)").get()
             poster = item.css("img::attr(data-src)").get()

             if title and href:
                 results.append(SearchResult(
                     title   = title,
                     url     = self.fix_url(href),
                     poster  = self.fix_url(poster)
                 ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        resp = await self.httpx.get(url)
        sel  = Selector(resp.text)

        title       = sel.css("div.detail::attr(title)").get()
        poster      = sel.css("div.move_k img::attr(data-src)").get()
        description = sel.css("div.desc.yeniscroll p::text").get()
        rating      = sel.css("span.info span.imdb::text").get()

        tags   = sel.css("div.detail span a::text").getall()
        actors = sel.css("span.oyn p::text").getall()        # Might need splitting logic
        
        year = None
        info_text = sel.css("span.info::text").get()
        if info_text:
            year_match = re.search(r'\b(19\d{2}|20\d{2})\b', info_text)
            if year_match:
                year = year_match.group(1)
        
        # Bulunamadıysa tüm sayfada ara
        if not year:
            all_text = " ".join(sel.css("::text").getall())
            year_match = re.search(r'\b(19\d{2}|20\d{2})\b', all_text)
            if year_match:
                year = year_match.group(1)

        return MovieInfo(
            title       = title,
            url         = url,
            poster      = self.fix_url(poster),
            description = description,
            tags        = tags,
            rating      = rating,
            actors      = actors,
            year        = year
        )

    async def load_links(self, url: str) -> list[dict]:
        resp = await self.httpx.get(url)

        match = re.search(r"ilkpartkod\s*=\s*'([^']+)'", resp.text, re.IGNORECASE)
        if match:
             encoded = match.group(1)
             try:
                 decoded = base64.b64decode(encoded).decode('utf-8')
                 iframe_match = re.search(r'src="([^"]*)"', decoded)

                 if iframe_match:
                     iframe = iframe_match.group(1)
                     iframe = self.fix_url(iframe)
                     
                     data = await self.extract(iframe)
                     if data:
                         return [data]
             except Exception:
                 pass

        return []
