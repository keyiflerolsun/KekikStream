# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, MovieInfo, ExtractResult, HTMLHelper
import json, urllib.parse

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
        sel  = HTMLHelper(resp.text)

        results = []
        for item in sel.select("div.poster-with-subject, div.dark-segment div.poster-md.poster"):
            title  = sel.select_text("h2", item)
            href   = sel.select_attr("a", "href", item)
            poster = sel.select_attr("img", "data-srcset", item)

            if poster:
                poster = poster.split(",")[0].split(" ")[0]

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster) if poster else None
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        # Try to get dynamic keys from main page first
        c_key   = "ca1d4a53d0f4761a949b85e51e18f096"
        c_value = "MTc0NzI2OTAwMDU3ZTEwYmZjMDViNWFmOWIwZDViODg0MjU4MjA1ZmYxOThmZTYwMDdjMWQzMzliNzY5NzFlZmViMzRhMGVmNjgwODU3MGIyZA=="

        try:
            resp = await self.httpx.get(self.main_url)
            sel  = HTMLHelper(resp.text)

            cke = sel.select_attr("input[name='cKey']", "value")
            cval = sel.select_attr("input[name='cValue']", "value")

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
                            poster=self.fix_url(poster) if poster else None
                        ))
                return results

        except Exception:
            pass
        return []

    async def load_item(self, url: str) -> SeriesInfo:
        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)
        
        title    = sel.select_text("h1")

        poster_info = sel.select_attr("div.ui.items img", "data-srcset")
        poster = None
        if poster_info:
            parts = str(poster_info).split(",")
            for p in parts:
                if "1x" in p:
                    poster = p.strip().split(" ")[0]
                    break

        description = sel.select_text("p#tv-series-desc")

        tags    = [a.text(strip=True) for a in sel.select("div.item.categories a") if a.text(strip=True)]

        rating    = sel.select_text("span.color-imdb")

        actors = [h5.text(strip=True) for h5 in sel.select("div.content h5") if h5.text(strip=True)]

        year    = sel.select_text("span.item.year")
        if not year and title:
            # Try to extract year from title like "Movie Name(2024)"
            year_match = sel.regex_first(r"\((\d{4})\)", title)
            if year_match:
                year = year_match
        
        episodes = []
        episodes_box_list = sel.select("section.episodes-box")
        
        if episodes_box_list:
            episodes_box = episodes_box_list[0]
            # Sezon menüsünden sezon linklerini al
            season_menu = sel.select("div.ui.vertical.fluid.tabular.menu a.item", episodes_box)
            
            # Sezon tab içeriklerini al
            season_tabs = sel.select("div.ui.tab", episodes_box)
            
            # Eğer birden fazla sezon varsa, her sezon tab'ından bölümleri çek
            if season_tabs:
                for idx, season_tab in enumerate(season_tabs):
                    # Sezon numarasını belirle
                    current_season_no = idx + 1
                    
                    # Menüden sezon numarasını almaya çalış
                    if idx < len(season_menu):
                        menu_href = season_menu[idx].attrs.get("href", "")
                        match = sel.regex_first(r"sezon-(\d+)", menu_href)
                        if match:
                            current_season_no = int(match)
                    
                    # Bu sezon tab'ından bölüm linklerini çek
                    ep_links = sel.select("a[href*='bolum']", season_tab)
                    
                    seen_urls = set()
                    for ep_link in ep_links:
                        href = ep_link.attrs.get("href")
                        if not href or href in seen_urls:
                            continue
                        seen_urls.add(href)
                        
                        # Bölüm numarasını URL'den çıkar
                        ep_no = 0
                        match_ep = sel.regex_first(r"bolum-(\d+)", href)
                        if match_ep:
                            ep_no = int(match_ep)
                        
                        # Bölüm başlığını çıkar (önce title attribute, sonra text)
                        name = ep_link.attrs.get("title", "")
                        if not name:
                            name = sel.select_text("div.content div.header", ep_link)
                            if not name:
                                name = ep_link.text(strip=True)
                        
                        if href and ep_no > 0:
                            episodes.append(Episode(
                                season  = current_season_no,
                                episode = ep_no,
                                title   = name.strip() if name else f"{ep_no}. Bölüm",
                                url     = self.fix_url(href)
                            ))
        
        if episodes:
            return SeriesInfo(
                title    = title,
                url      = url,
                poster   = self.fix_url(poster) if poster else None,
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
                poster      = self.fix_url(poster) if poster else None,
                description = description,
                rating      = rating,
                tags        = tags,
                actors      = actors,
                year        = year
            )

    async def load_links(self, url: str) -> list[ExtractResult]:
        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)
        
        iframe = sel.select_attr("iframe", "src")

        if not iframe:
            return []
            
        iframe_url = self.fix_url(iframe)
        
        # Try to extract actual video URL, fallback to raw iframe if fails
        try:
            result = await self.extract(iframe_url)
            if result:
                return [result] if not isinstance(result, list) else result
        except Exception:
            pass
        
        # Fallback: return raw iframe URL
        return [ExtractResult(
            url  = iframe_url,
            name = "Sinefy Player"
        )]
