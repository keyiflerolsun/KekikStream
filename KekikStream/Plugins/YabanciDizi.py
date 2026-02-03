# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, MovieInfo, Episode, ExtractResult, HTMLHelper
import asyncio, time

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
        istek   = await self.httpx.get(
            url     = url if page == 1 else f"{url}/{page}",
            headers = {"Referer": f"{self.main_url}/"}
        )
        secici  = HTMLHelper(istek.text)

        results = []
        for item in secici.select("li.mb-lg, li.segment-poster"):
            title  = secici.select_text("h2", item)
            href   = secici.select_attr("a", "href", item)
            poster = secici.select_attr("img", "src", item)

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek = await self.httpx.post(
            url     = f"{self.main_url}/search?qr={query}",
            headers = {
                "X-Requested-With" : "XMLHttpRequest",
                "Referer"          : f"{self.main_url}/"
            }
        )
        
        try:
            raw = istek.json()
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
                        poster = self.fix_url(poster)
                    ))
            return results
        except Exception:
            return []

    async def load_item(self, url: str) -> SeriesInfo | MovieInfo:
        istek  = await self.httpx.get(url, follow_redirects=True)
        secici = HTMLHelper(istek.text)

        title       = (secici.select_attr("meta[property='og:title']", "content") or "").split("|")[0].strip() or secici.select_text("h1")
        poster      = secici.select_poster("meta[property='og:image']")
        description = secici.select_text("p#tv-series-desc")
        year        = secici.extract_year("td div.truncate")
        tags        = secici.meta_list("Türü", container_selector="div.item")
        rating      = secici.meta_value("IMDb Puanı", container_selector="div.item")
        duration    = int(secici.regex_first(r"(\d+)", secici.meta_value("Süre", container_selector="div.item")) or 0)
        actors      = secici.meta_list("Oyuncular", container_selector="div.item") or secici.select_texts("div#common-cast-list div.item h5")

        common_info = {
            "url"         : url,
            "poster"      : self.fix_url(poster),
            "title"       : title,
            "description" : description,
            "tags"        : tags,
            "rating"      : rating,
            "year"        : year,
            "actors"      : actors,
            "duration"    : duration
        }

        if "/film/" in url:
            return MovieInfo(**common_info)

        episodes = []
        for bolum in secici.select("div.episodes-list div.ui td:has(h6)"):
            link = secici.select_first("a", bolum)
            if link:
                href = link.attrs.get("href")
                name = secici.select_text("h6", bolum) or link.text(strip=True)
                s, e = secici.extract_season_episode(href)
                episodes.append(Episode(
                    season  = s or 1,
                    episode = e or 1,
                    title   = name,
                    url     = self.fix_url(href)
                ))

        if episodes and (episodes[0].episode or 0) > (episodes[-1].episode or 0):
            episodes.reverse()

        return SeriesInfo(**common_info, episodes=episodes)

    async def load_links(self, url: str) -> list[ExtractResult]:
        loop = asyncio.get_event_loop()

        # 1. Ana sayfayı çek
        istek = await loop.run_in_executor(None, lambda: self.cloudscraper.get(url, headers={"Referer": f"{self.main_url}/"}))
        secici = HTMLHelper(istek.text)

        results = []
        timestamp_ms = int(time.time() * 1000) - 50000

        # 2. Dil Tablarını Bul
        tabs = secici.select("div#series-tabs a")

        async def process_tab(tab_el):
            data_eid  = tab_el.attrs.get("data-eid")
            data_type = tab_el.attrs.get("data-type") # 1: Altyazı, 2: Dublaj
            if not data_eid or not data_type:
                return []

            dil_adi = "Dublaj" if data_type == "2" else "Altyazı"

            try:
                post_resp = await loop.run_in_executor(None, lambda: self.cloudscraper.post(
                    url     = f"{self.main_url}/ajax/service",
                    headers = {
                        "X-Requested-With" : "XMLHttpRequest",
                        "Referer"          : url
                    },
                    data    = {
                        "lang"    : data_type,
                        "episode" : data_eid,
                        "type"    : "langTab"
                    },
                    cookies = {"udys": str(timestamp_ms)}
                ))

                res_json = post_resp.json()
                if not res_json.get("data"):
                    return []

                res_sel = HTMLHelper(res_json["data"])
                sources = []

                for item in res_sel.select("div.item"):
                    name      = item.text(strip=True)
                    data_link = item.attrs.get("data-link")
                    if not data_link:
                        continue

                    # Link normalizasyonu
                    safe_link = data_link.replace("/", "_").replace("+", "-")

                    # API Endpoint belirleme
                    api_path = None
                    if "VidMoly" in name:
                        api_path = "moly"
                    elif "Okru" in name:
                        api_path = "ruplay"
                    elif "Mac" in name:
                        api_path = "drive"

                    if api_path:
                        sources.append({
                            "name"    : name,
                            "api_url" : f"{self.main_url}/api/{api_path}/{safe_link}",
                            "dil"     : dil_adi
                        })

                tab_results = []
                for src in sources:
                    try:
                        # API sayfasını çekip içindeki iframe'i bulalım
                        api_resp = await loop.run_in_executor(None, lambda: self.cloudscraper.get(
                            src["api_url"], 
                            headers={"Referer": f"{self.main_url}/"},
                            cookies={"udys": str(timestamp_ms)}
                        ))

                        api_sel = HTMLHelper(api_resp.text)
                        iframe  = api_sel.select_attr("iframe", "src")

                        if not iframe and "drive" in src["api_url"]:
                            t_sec = int(time.time())
                            drives_url = f"{src['api_url'].replace('/api/drive/', '/api/drives/')}?t={t_sec}"
                            api_resp = await loop.run_in_executor(None, lambda: self.cloudscraper.get(
                                drives_url,
                                headers={"Referer": src["api_url"]},
                                cookies={"udys": str(timestamp_ms)}
                            ))
                            api_sel = HTMLHelper(api_resp.text)
                            iframe  = api_sel.select_attr("iframe", "src")

                        if iframe:
                            prefix = f"{src['dil']} | {src['name']}"
                            extracted = await self.extract(self.fix_url(iframe), prefix=prefix)
                            if extracted:
                                tab_results.extend(extracted if isinstance(extracted, list) else [extracted])
                    except Exception:
                        continue
                return tab_results

            except Exception:
                return []

        if tabs:
            results_groups = await asyncio.gather(*(process_tab(tab) for tab in tabs))
            for group in results_groups:
                results.extend(group)
        else:
            # Tab yoksa mevcut sayfada iframe ara
            iframe = secici.select_attr("iframe", "src")
            if iframe:
                extracted = await self.extract(self.fix_url(iframe), name_override="Main")
                if extracted:
                    results.extend(extracted if isinstance(extracted, list) else [extracted])

        # Duplicate kontrolü
        unique_results = []
        seen = set()
        for res in results:
            if res.url and res.url not in seen:
                unique_results.append(res)
                seen.add(res.url)

        return unique_results
