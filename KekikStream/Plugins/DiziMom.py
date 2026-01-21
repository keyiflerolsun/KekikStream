# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
from json             import dumps, loads
import re

class DiziMom(PluginBase):
    name        = "DiziMom"
    language    = "tr"
    main_url    = "https://www.dizimom.one"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Binlerce yerli yabancı dizi arşivi, tüm sezonlar, kesintisiz bölümler. Sadece dizi izle, Dizimom heryerde seninle!"

    main_page = {
        f"{main_url}/tum-bolumler/page"        : "Son Bölümler",
        f"{main_url}/yerli-dizi-izle/page"     : "Yerli Diziler",
        f"{main_url}/yabanci-dizi-izle/page"   : "Yabancı Diziler",
        f"{main_url}/tv-programlari-izle/page" : "TV Programları",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek   = await self.httpx.get(f"{url}/{page}/")
        helper  = HTMLHelper(istek.text)

        if "/tum-bolumler/" in url:
            items = helper.select("div.episode-box")
            results = []
            for item in items:
                name_el = helper.select_first("div.episode-name a", item)
                if not name_el: continue
                name = name_el.text(strip=True).split(" izle")[0]
                title = name.replace(".Sezon ", "x").replace(".Bölüm", "")
                
                ep_href = self.fix_url(name_el.attrs.get("href"))
                pass 
            
            # Revert to standard categories if "tum-bolumler" is complex
            return [] 
        else:
            items = helper.select("div.single-item")
            return [
                MainPageResult(
                    category = category,
                    title    = helper.select_text("div.categorytitle a", item).split(" izle")[0],
                    url      = self.fix_url(helper.select_attr("div.categorytitle a", "href", item)),
                    poster   = self.fix_url(helper.select_attr("div.cat-img img", "src", item))
                )
                for item in items
            ]

    async def search(self, query: str) -> list[SearchResult]:
        url = f"{self.main_url}/?s={query}"
        istek = await self.httpx.get(url)
        helper = HTMLHelper(istek.text)
        items = helper.select("div.single-item")
        
        return [
            SearchResult(
                title  = helper.select_text("div.categorytitle a", item).split(" izle")[0],
                url    = self.fix_url(helper.select_attr("div.categorytitle a", "href", item)),
                poster = self.fix_url(helper.select_attr("div.cat-img img", "src", item))
            )
            for item in items
        ]

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        helper = HTMLHelper(istek.text)

        title_raw = helper.select_text("div.title h1")
        title = title_raw.split(" izle")[0] if title_raw else "Bilinmiyor"
        
        poster = self.fix_url(helper.select_attr("div.category_image img", "src"))
        
        # Custom extraction for fields that were using xpath_text
        year = None
        rating = None
        actors = None
        
        # Regex approach based on debug output (multiline support)
        # Context: <span class="dizimeta"><i class="fas fa-globe"></i> Yapım Yılı : </span>\n 2022
        year_val_all = helper.regex_all(r"Yapım Yılı\s*:\s*(?:</span>)?\s*(\d{4})", flags=re.DOTALL)
        if year_val_all:
             year = int(year_val_all[0])
            
        # Context: <span class="dizimeta"><i class="fas fa-star"></i> IMDB : </span>\n 4.5
        rating_val_all = helper.regex_all(r"IMDB\s*:\s*(?:</span>)?\s*([\d\.]+)", flags=re.DOTALL)
        if rating_val_all:
            rating = rating_val_all[0]
            
        actors_val = helper.regex_first(r"Oyuncular\s*:\s*(.+?)(?:</div>|<br|$)")
        if not actors_val:
             # Try selecting the div text directly if regex fails due to HTML tags
             # Find div containing "Oyuncular :"
             all_divs = helper.select("div")
             for div in all_divs:
                 txt = div.text()
                 if "Oyuncular :" in txt:
                     actors_val = txt.split("Oyuncular :")[1].strip()
                     break
        
        if actors_val:
             # Remove footer / junk from actors
             if "IMDB :" in actors_val:
                 actors_val = actors_val.split("IMDB :")[0].strip()
                 
             if "IMDB :" in actors_val:
                 actors_val = actors_val.split("IMDB :")[0].strip()
                 
             # Remove '×' and other junk if present at end
             if "×" in actors_val:
                 actors_val = actors_val.split("×")[0].strip()

             # Remove simple tags if any remaining
             clean_actors = [a.strip() for a in actors_val.split(",")]
             # Filter empty
             clean_actors = [a for a in clean_actors if a]
             
             actors = ", ".join(clean_actors)
             
        description_raw = helper.select_text("div.category_desc")
        description = None
        if description_raw:
             # Clean header "The Librarians izle..." etc. if present, usually it is fine.
             # Clean "IMDB :" if attached
             if "IMDB :" in description_raw:
                 description_raw = description_raw.split("IMDB :")[0].strip()
             
             # Clean footer text start
             # The footer block usually starts with "Dizimom, dizi ve film..."
             if "Dizimom," in description_raw:
                 description = description_raw.split("Dizimom,")[0].strip()
             elif "dizi izle film izle" in description_raw:
                 description = description_raw.split("dizi izle film izle")[0].strip()
             else:
                  description = description_raw

             # Fallback cleanup for JSON
             if description and "{" in description:
                  description = description.split("{")[0].strip()

        tags = helper.select_all_text("div.genres a")
        
        # Improved year regex
        if not year:
             # Look for "Yapım Yılı : 2014" pattern in ANY text
             # Get all text from category_text which usually contains it
             meta_text = helper.select_text("div.category_text")
             if meta_text:
                 match = re.search(r"Yapım Yılı\s*:\s*(\d{4})", meta_text)
                 if match:
                     year = int(match.group(1))

        episodes = []
        ep_items = helper.select("div.bolumust")
        for item in ep_items:
            ep_name_raw = helper.select_text("div.baslik", item)
            ep_href = self.fix_url(helper.select_attr("a", "href", item))
            
            if ep_name_raw:
                # 1.Sezon 1.Bölüm
                s_m = re.search(r"(\d+)\.Sezon", ep_name_raw)
                e_m = re.search(r"(\d+)\.Bölüm", ep_name_raw)
                
                season = int(s_m.group(1)) if s_m else 1
                episode = int(e_m.group(1)) if e_m else 1
                
                name = ep_name_raw.split(" izle")[0].replace(title, "").strip()
                
                episodes.append(Episode(
                    season  = season,
                    episode = episode,
                    title   = name,
                    url     = ep_href
                ))

        return SeriesInfo(
            url         = url,
            poster      = poster,
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = str(year) if year else None,
            actors      = actors,
            episodes    = episodes
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        # Login simulation headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "sec-ch-ua": 'Not/A)Brand";v="8", "Chromium";v="137", "Google Chrome";v="137"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": "Android"
        }
        
        # Simulate login (as seen in Kotlin)
        login_url = f"{self.main_url}/wp-login.php"
        login_data = {
            "log": "keyiflerolsun",
            "pwd": "12345",
            "rememberme": "forever",
            "redirect_to": self.main_url
        }
        
        await self.httpx.post(login_url, headers=headers, data=login_data)
        
        istek = await self.httpx.get(url, headers=headers)
        helper = HTMLHelper(istek.text)
        
        iframes = []
        
        main_iframe = helper.select_attr("iframe[src]", "src")
        if main_iframe:
            iframes.append(main_iframe)
            
        sources = helper.select("div.sources a")
        for source in sources:
            href = source.attrs.get("href")
            if href:
                sub_istek = await self.httpx.get(href, headers=headers)
                sub_helper = HTMLHelper(sub_istek.text)
                sub_iframe = sub_helper.select_attr("div.video p iframe", "src")
                if sub_iframe:
                    iframes.append(sub_iframe)
                    
        results = []
        for iframe_url in iframes:
            # Check for known extractors
            if iframe_url.startswith("//"):
                iframe_url = f"https:{iframe_url}"
             
            extract_result = await self.extract(iframe_url)
            if extract_result:
                if isinstance(extract_result, list):
                    results.extend(extract_result)
                else:
                    results.append(extract_result)
            else:
                 results.append(ExtractResult(
                    url  = iframe_url,
                    name = f"{self.name} | External",
                    referer = self.main_url
                ))
                
        return results
