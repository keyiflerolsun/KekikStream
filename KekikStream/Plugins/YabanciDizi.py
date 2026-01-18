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

        og_title = sel.select_attr("meta[property='og:title']", "content")
        title    = og_title.split("|")[0].strip() if og_title else sel.select_text("h1")
        
        poster   = sel.select_attr("meta[property='og:image']", "content")
        description = sel.select_text("p#tv-series-desc")
        
        year = sel.select_text("td div.truncate")
        if year:
            year = year.strip()
            
        tags = []
        rating = None
        duration = None
        year = None
        actors = []
        for item in sel.select("div.item"):
            text = item.text(strip=True)
            if "T\u00fcr\u00fc:" in text:
                tags = [t.strip() for t in text.replace("T\u00fcr\u00fc:", "").split(",")]
            elif "IMDb Puan\u0131" in text:
                rating = text.replace("IMDb Puan\u0131", "").strip()
            elif "Yap\u0131m Y\u0131l\u0131" in text:
                year_match = sel.regex_first(r"(\d{4})", text)
                if year_match:
                    year = year_match
            elif "Takip\u00e7iler" in text:
                continue
            elif "S\u00fcre" in text:
                dur_match = sel.regex_first(r"(\d+)", text)
                if dur_match:
                    duration = dur_match
            elif "Oyuncular:" in text:
                actors = [a.text(strip=True) for a in sel.select("a", item)]
        
        if not actors:
            actors = [a.text(strip=True) for a in sel.select("div#common-cast-list div.item h5")]
        
        trailer_match = sel.regex_first(r"embed\/(.*)\?rel", resp.text)
        trailer = f"https://www.youtube.com/embed/{trailer_match}" if trailer_match else None

        if "/film/" in url:
            return MovieInfo(
                title       = title,
                url         = url,
                poster      = self.fix_url(poster) if poster else None,
                description = description,
                rating      = rating,
                tags        = tags,
                actors      = actors,
                year        = year,
                duration    = int(duration) if duration and duration.isdigit() else None
            )
        else:
            episodes = []
            for bolum_item in sel.select("div.episodes-list div.ui td:has(h6)"):
                link_el = sel.select_first("a", bolum_item)
                if not link_el: continue
                
                bolum_href = link_el.attrs.get("href")
                bolum_name = sel.select_text("h6", bolum_item) or link_el.text(strip=True)
                
                season = sel.regex_first(r"sezon-(\d+)", bolum_href)
                episode = sel.regex_first(r"bolum-(\d+)", bolum_href)

                ep_season = int(season) if season and season.isdigit() else None
                ep_episode = int(episode) if episode and episode.isdigit() else None

                episodes.append(Episode(
                    season  = ep_season,
                    episode = ep_episode,
                    title   = bolum_name,
                    url     = self.fix_url(bolum_href)
                ))

            if episodes and (episodes[0].episode or 0) > (episodes[-1].episode or 0):
                episodes.reverse()

            return SeriesInfo(
                title       = title,
                url         = url,
                poster      = self.fix_url(poster) if poster else None,
                description = description,
                rating      = rating,
                tags        = tags,
                actors      = actors,
                year        = year,
                episodes    = episodes
            )

    async def load_links(self, url: str) -> list[ExtractResult]:
        resp = await self.httpx.get(url, headers={"Referer": f"{self.main_url}/"})
        sel  = HTMLHelper(resp.text)
        
        results = []
        
        # Method 1: alternatives-for-this
        for alt in sel.select("div.alternatives-for-this div.item:not(.active)"):
            data_hash = alt.attrs.get("data-hash")
            data_link = alt.attrs.get("data-link")
            q_type    = alt.attrs.get("data-querytype")
            
            if not data_hash or not data_link: continue
            
            try:
                post_resp = await self.httpx.post(
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
                post_resp = await self.httpx.post(
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

    async def _fetch_and_extract(self, iframe_url, prefix=""):
        # Initial fetch
        resp = await self.httpx.get(
            iframe_url,
            headers = {"Referer": f"{self.main_url}/"},
            cookies = {"udys": "1760709729873", "level": "1"}
        )
        
        # Handle "Lütfen bekleyiniz" check from Kotlin
        if "Lütfen bekleyiniz" in resp.text:
            await asyncio.sleep(1)
            timestamp = int(time.time())
            # Retry with t=timestamp as in Kotlin
            sep = "&" if "?" in iframe_url else "?"
            resp = await self.httpx.get(
                f"{iframe_url}{sep}t={timestamp}",
                headers = {"Referer": f"{self.main_url}/"},
                cookies = resp.cookies # Use cookies from first response
            )

        sel = HTMLHelper(resp.text)
        final_iframe = sel.select_attr("iframe", "src")
        
        if final_iframe:
            final_url = self.fix_url(final_iframe)
            return await self.extract(final_url, referer=f"{self.main_url}/", prefix=prefix)
        
        return None
