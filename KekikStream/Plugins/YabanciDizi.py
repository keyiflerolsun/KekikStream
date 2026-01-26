# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, MovieInfo, Episode, ExtractResult, HTMLHelper
import json, asyncio, time

class YabanciDizi(PluginBase):
    name        = "YabanciDizi"
    language    = "tr"
    main_url    = "https://yabancidizi.so"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Yabancidizi.so platformu üzerinden en güncel yabancı dizileri ve filmleri izleyebilir, favori içeriklerinizi takip edebilirsiniz."

    main_page = {
        f"{main_url}/kesfet/eyJvcmRlciI6ImRhdGVfYm90dG9tIiwia2F0ZWdvcnkiOlsiMTciXX0=" : "Diziler",
        f"{main_url}/kesfet/eyJvcmRlciI6ImRhdGVfYm90dG9tIiwia2F0ZWdvcnkiOlsiMTgiXX0=" : "Filmler",
        f"{main_url}/kesfet/eyJvcmRlciI6ImRhdGVfYm90dG9tIiwiY291bnRyeSI6eyJLUiI6IktSIn19" : "Kdrama",
        f"{main_url}/kesfet/eyJvcmRlciI6ImRhdGVfYm90dG9tIiwiY291bnRyeSI6eyJKUCI6IkpQIn0sImNhdGVnb3J5IjpbXX0=" : "Jdrama",
        f"{main_url}/kesfet/eyJvcmRlciI6ImRhdGVfYm90dG9tIiwiY2F0ZWdvcnkiOnsiMyI6IjMifX0=" : "Animasyon",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        full_url = url if page == 1 else f"{url}/{page}"
        
        resp = await self.httpx.get(full_url, headers={"Referer": f"{self.main_url}/"})
        sel  = HTMLHelper(resp.text)

        results = []
        for item in sel.select("li.mb-lg, li.segment-poster"):
            title  = sel.select_text("h2", item)
            href   = sel.select_attr("a", "href", item)
            poster = sel.select_attr("img", "src", item)
            score  = sel.select_text("span.rating", item)

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster) if poster else None,
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        search_url = f"{self.main_url}/search?qr={query}"
        
        headers = {
            "X-Requested-With" : "XMLHttpRequest",
            "Referer"          : f"{self.main_url}/"
        }
        
        resp = await self.httpx.post(search_url, headers=headers)
        
        try:
            raw = resp.json()
            # Kotlin mapping: JsonResponse -> Data -> ResultItem
            res_array = raw.get("data", {}).get("result", [])
            
            results = []
            for item in res_array:
                title  = item.get("s_name")
                image  = item.get("s_image")
                slug   = item.get("s_link")
                s_type = item.get("s_type") # 0: dizi, 1: film
                
                poster = f"{self.main_url}/uploads/series/{image}" if image else None
                
                if s_type == "1":
                    href = f"{self.main_url}/film/{slug}"
                else:
                    href = f"{self.main_url}/dizi/{slug}"

                if title and slug:
                    results.append(SearchResult(
                        title  = title,
                        url    = self.fix_url(href),
                        poster = self.fix_url(poster) if poster else None
                    ))
            return results
        except Exception:
            return []

    async def load_item(self, url: str) -> SeriesInfo | MovieInfo:
        resp = await self.httpx.get(url, follow_redirects=True)
        sel  = HTMLHelper(resp.text)

        title       = (sel.select_attr("meta[property='og:title']", "content") or "").split("|")[0].strip() or sel.select_text("h1")
        poster      = sel.select_poster("meta[property='og:image']")
        description = sel.select_text("p#tv-series-desc")
        year        = sel.extract_year("td div.truncate")
        tags        = sel.meta_list("Türü", container_selector="div.item")
        rating      = sel.meta_value("IMDb Puanı", container_selector="div.item")
        duration    = int(sel.regex_first(r"(\d+)", sel.meta_value("Süre", container_selector="div.item")) or 0)
        actors      = sel.meta_list("Oyuncular", container_selector="div.item") or sel.select_texts("div#common-cast-list div.item h5")
        
        common_info = {
            "url"         : url,
            "poster"      : self.fix_url(poster) if poster else None,
            "title"       : title or "Bilinmiyor",
            "description" : description,
            "tags"        : tags,
            "rating"      : rating,
            "year"        : str(year) if year else None,
            "actors"      : actors,
            "duration"    : duration
        }

        if "/film/" in url:
            return MovieInfo(**common_info)
        
        episodes = []
        for bolum in sel.select("div.episodes-list div.ui td:has(h6)"):
            link = sel.select_first("a", bolum)
            if link:
                href = link.attrs.get("href")
                name = sel.select_text("h6", bolum) or link.text(strip=True)
                s, e = sel.extract_season_episode(href)
                episodes.append(Episode(season=s or 1, episode=e or 1, title=name, url=self.fix_url(href)))

        if episodes and (episodes[0].episode or 0) > (episodes[-1].episode or 0):
            episodes.reverse()

        return SeriesInfo(**common_info, episodes=episodes)

    async def load_links(self, url: str) -> list[ExtractResult]:
        # Use cloudscraper to bypass Cloudflare
        resp = self.cloudscraper.get(url, headers={"Referer": f"{self.main_url}/"})
        sel  = HTMLHelper(resp.text)
        
        results = []
        
        # Method 1: alternatives-for-this (include active too)
        for alt in sel.select("div.alternatives-for-this div.item"):
            data_hash = alt.attrs.get("data-hash")
            data_link = alt.attrs.get("data-link")
            q_type    = alt.attrs.get("data-querytype")
            
            if not data_hash or not data_link: continue
            
            try:
                post_resp = self.cloudscraper.post(
                    f"{self.main_url}/ajax/service",
                    data = {
                        "link"      : data_link,
                        "hash"      : data_hash,
                        "querytype" : q_type,
                        "type"      : "videoGet"
                    },
                    headers = {
                        "X-Requested-With" : "XMLHttpRequest",
                        "Referer"          : f"{self.main_url}/"
                    },
                    cookies = {"udys": "1760709729873", "level": "1"}
                )
                
                service_data = post_resp.json()
                api_iframe   = service_data.get("api_iframe")
                if api_iframe:
                    extract_res = await self._fetch_and_extract(api_iframe, prefix="Alt")
                    if extract_res:
                        results.extend(extract_res if isinstance(extract_res, list) else [extract_res])
            except Exception:
                continue

        # Method 2: pointing[data-eid]
        for id_el in sel.select("a.ui.pointing[data-eid]"):
            dil = id_el.text(strip=True)
            v_lang = "tr" if "Dublaj" in dil else "en"
            data_eid = id_el.attrs.get("data-eid")
            
            try:
                post_resp = self.cloudscraper.post(
                    f"{self.main_url}/ajax/service",
                    data = {
                        "e_id"   : data_eid,
                        "v_lang" : v_lang,
                        "type"   : "get_whatwehave"
                    },
                    headers = {
                        "X-Requested-With" : "XMLHttpRequest",
                        "Referer"          : f"{self.main_url}/"
                    },
                    cookies = {"udys": "1760709729873", "level": "1"}
                )
                
                service_data = post_resp.json()
                api_iframe   = service_data.get("api_iframe")
                if api_iframe:
                    extract_res = await self._fetch_and_extract(api_iframe, prefix=dil)
                    if extract_res:
                        results.extend(extract_res if isinstance(extract_res, list) else [extract_res])
            except Exception:
                continue

        return results

    def _fetch_and_extract_sync(self, iframe_url, prefix=""):
        """Synchronous helper for _fetch_and_extract using cloudscraper."""
        # Initial fetch
        resp = self.cloudscraper.get(
            iframe_url,
            headers = {"Referer": f"{self.main_url}/"},
            cookies = {"udys": "1760709729873", "level": "1"}
        )
        
        # Handle "Lütfen bekleyiniz" check from Kotlin
        if "Lütfen bekleyiniz" in resp.text:
            import time as time_module
            time_module.sleep(1)
            timestamp = int(time_module.time())
            # Retry with t=timestamp as in Kotlin
            sep = "&" if "?" in iframe_url else "?"
            resp = self.cloudscraper.get(
                f"{iframe_url}{sep}t={timestamp}",
                headers = {"Referer": f"{self.main_url}/"},
                cookies = resp.cookies # Use cookies from first response
            )

        sel = HTMLHelper(resp.text)
        final_iframe = sel.select_attr("iframe", "src")
        
        return final_iframe

    async def _fetch_and_extract(self, iframe_url, prefix=""):
        final_iframe = self._fetch_and_extract_sync(iframe_url, prefix)
        
        if final_iframe:
            final_url = self.fix_url(final_iframe)
            return await self.extract(final_url, referer=f"{self.main_url}/", prefix=prefix)
        
        return None
