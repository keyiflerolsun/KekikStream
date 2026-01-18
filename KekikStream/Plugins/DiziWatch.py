# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
import urllib.parse

class DiziWatch(PluginBase):
    name        = "DiziWatch"
    language    = "tr"
    main_url    = "https://diziwatch.to"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Diziwatch; en güncel yabancı dizileri ve animeleri, Türkçe altyazılı ve dublaj seçenekleriyle izleyebileceğiniz platform."

    main_page = {
        f"{main_url}/episodes" : "Yeni Bölümler",
        "9"   : "Aksiyon", 
        "17"  : "Animasyon",
        "5"   : "Bilim Kurgu",
        "2"   : "Dram",
        "12"  : "Fantastik",
        "3"   : "Gizem",
        "4"   : "Komedi",
        "8"   : "Korku",
        "24"  : "Macera",
        "14"  : "Müzik",
        "7"   : "Romantik",
        "23"  : "Spor",
        "1"   : "Suç",
    }

    async def _init_session(self):
        if getattr(self, "c_key", None) and getattr(self, "c_value", None):
            return
        
        # Fetch anime-arsivi to get CSRF tokens
        resp = await self.httpx.get(f"{self.main_url}/anime-arsivi")
        sel  = HTMLHelper(resp.text)
        
        # form.bg-[rgba(255,255,255,.15)] > input
        # We can just look for the first two inputs in that specific form
        inputs = sel.select("form.bg-\\[rgba\\(255\\,255\\,255\\,\\.15\\)\\] input")
        if len(inputs) >= 2:
            self.c_key   = inputs[0].attrs.get("value")
            self.c_value = inputs[1].attrs.get("value")

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        await self._init_session()
        
        if url.startswith("https://"):
            full_url = f"{url}?page={page}"
            resp = await self.httpx.get(full_url, headers={"Referer": f"{self.main_url}/"})
            sel  = HTMLHelper(resp.text)
            items = sel.select("div.swiper-slide a")
        else:
            # Category ID based
            full_url = f"{self.main_url}/anime-arsivi?category={url}&minImdb=&name=&release_year=&sort=date_desc&page={page}"
            resp = await self.httpx.get(full_url, headers={"Referer": f"{self.main_url}/"})
            sel  = HTMLHelper(resp.text)
            items = sel.select("div.content-inner a")

        results = []
        for item in items:
            title  = sel.select_text("h2", item)
            href   = item.attrs.get("href") if item.tag == "a" else sel.select_attr("a", "href", item)
            poster = sel.select_attr("img", "src", item) or sel.select_attr("img", "data-src", item)

            if title and href:
                # If it's an episode link, clean it to get show link
                # Regex in Kotlin: /sezon-\d+/bolum-\d+/?$
                clean_href = HTMLHelper(href).regex_replace(r"/sezon-\d+/bolum-\d+/?$", "")
                
                # If cleaning changed something, it was an episode link, maybe add it to title
                if clean_href != href:
                    se_info = sel.select_text("div.flex.gap-1.items-center", item)
                    if se_info:
                        title = f"{title} - {se_info}"

                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(clean_href),
                    poster   = self.fix_url(poster) if poster else None
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        await self._init_session()
        
        post_url = f"{self.main_url}/bg/searchcontent"
        data = {
            "cKey"       : self.c_key,
            "cValue"     : self.c_value,
            "searchterm" : query
        }
        
        headers = {
            "X-Requested-With" : "XMLHttpRequest",
            "Accept"           : "application/json, text/javascript, */*; q=0.01",
            "Referer"          : f"{self.main_url}/"
        }
        
        resp = await self.httpx.post(post_url, data=data, headers=headers)
        
        try:
            raw = resp.json()
            # Kotlin maps this to ApiResponse -> DataWrapper -> Icerikler
            res_array = raw.get("data", {}).get("result", [])
            
            results = []
            for item in res_array:
                title  = item.get("object_name", "").replace("\\", "")
                slug   = item.get("used_slug", "").replace("\\", "")
                poster = item.get("object_poster_url", "")
                
                # Cleanup poster URL as in Kotlin
                if poster:
                    poster = poster.replace("images-macellan-online.cdn.ampproject.org/i/s/", "") \
                                   .replace("file.dizilla.club", "file.macellan.online") \
                                   .replace("images.dizilla.club", "images.macellan.online") \
                                   .replace("images.dizimia4.com", "images.macellan.online") \
                                   .replace("file.dizimia4.com", "file.macellan.online")
                    poster = HTMLHelper(poster).regex_replace(r"(file\.)[\w\.]+\/?", r"\1macellan.online/")
                    poster = HTMLHelper(poster).regex_replace(r"(images\.)[\w\.]+\/?", r"\1macellan.online/")
                    poster = poster.replace("/f/f/", "/630/910/")

                if title and slug:
                    results.append(SearchResult(
                        title  = title,
                        url    = self.fix_url(slug),
                        poster = self.fix_url(poster) if poster else None
                    ))
            return results
        except Exception:
            return []

    async def load_item(self, url: str) -> SeriesInfo:
        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)

        title    = sel.select_text("h2")
        poster   = sel.select_attr("img.rounded-md", "src")
        description = sel.select_text("div.text-sm")
        
        year = sel.regex_first(r"Yap\u0131m Y\u0131l\u0131\s*:\s*(\d+)", resp.text)
        
        tags = []
        tags_raw = sel.regex_first(r"T\u00fcr\s*:\s*([^<]+)", resp.text)
        if tags_raw:
            tags = [t.strip() for t in tags_raw.split(",")]

        rating = sel.select_text(".font-semibold.text-white")
        if rating:
            rating = rating.replace(",", ".").strip()

        actors = [a.text(strip=True) for a in sel.select("span.valor a")]
        
        trailer_match = sel.regex_first(r"embed\/(.*)\?rel", resp.text)
        trailer = f"https://www.youtube.com/embed/{trailer_match}" if trailer_match else None

        duration_text = sel.select_text("span.runtime")
        duration = duration_text.split(" ")[0] if duration_text else None

        episodes = []
        # ul a handles episodes
        for ep_link in sel.select("ul a"):
            href = ep_link.attrs.get("href")
            if not href or "/sezon-" not in href:
                continue
                
            ep_name = sel.select_text("span.hidden.sm\\:block", ep_link)
            
            season_match = sel.regex_first(r"sezon-(\d+)", href)
            episode_match = sel.regex_first(r"bolum-(\d+)", href)
            
            season = season_match if season_match else None
            episode_num = episode_match if episode_match else None

            episodes.append(Episode(
                season  = int(season) if season and season.isdigit() else None,
                episode = int(episode_num) if episode_num and episode_num.isdigit() else None,
                title   = ep_name if ep_name else f"{season}x{episode_num}",
                url     = self.fix_url(href)
            ))

        return SeriesInfo(
            title       = title,
            url         = url,
            poster      = self.fix_url(poster) if poster else None,
            description = description,
            rating      = rating,
            tags        = tags,
            actors      = actors,
            year        = year,
            episodes    = episodes,
            duration    = int(duration) if duration and str(duration).isdigit() else None
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)
        
        iframe = sel.select_attr("iframe", "src")
        if not iframe:
            return []
            
        iframe_url = self.fix_url(iframe)
        data = await self.extract(iframe_url, referer=f"{self.main_url}/")
        
        if not data:
            return []
            
        return data if isinstance(data, list) else [data]
