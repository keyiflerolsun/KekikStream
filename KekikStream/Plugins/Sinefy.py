# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, MovieInfo, ExtractResult, HTMLHelper
import json, contextlib, asyncio

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

        istek  = await self.httpx.get(full_url)
        secici = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.poster-with-subject, div.dark-segment div.poster-md.poster"):
            title  = secici.select_text("h2", item)
            href   = secici.select_attr("a", "href", item)
            poster = secici.select_attr("img", "data-srcset", item)

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

        with contextlib.suppress(Exception):
            istek = await self.httpx.get(self.main_url)
            secici  = HTMLHelper(istek.text)

            cke  = secici.select_attr("input[name='cKey']", "value")
            cval = secici.select_attr("input[name='cValue']", "value")

            if cke and cval:
                c_key   = cke
                c_value = cval

        response = await self.httpx.post(
            url     = f"{self.main_url}/bg/searchcontent",
            headers = {
                "User-Agent"       : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:134.0) Gecko/20100101 Firefox/134.0",
                "Accept"           : "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With" : "XMLHttpRequest",
                "Content-Type"     : "application/x-www-form-urlencoded; charset=UTF-8"
            },
            data    = {
                "cKey"       : c_key,
                "cValue"     : c_value,
                "searchTerm" : query
            }
        )

        with contextlib.suppress(Exception):
            # Extract JSON data from response (might contain garbage chars at start)
            raw = response.text
            json_start = raw.find('{')
            if json_start != -1:
                clean_json = raw[json_start:]
                data       = json.loads(clean_json)

                results = []
                # Result array is in data['data']['result']
                res_array = data.get("data", {}).get("result", [])

                if not res_array:
                    # Fallback manual parsing ?
                    pass

                for item in res_array:
                    name   = item.get("object_name")
                    slug   = item.get("used_slug")
                    poster = item.get("object_poster_url")

                    if name and slug:
                        if "cdn.ampproject.org" in poster:
                            poster = "https://images.macellan.online/images/movie/poster/180/275/80/" + poster.split("/")[-1]

                        results.append(SearchResult(
                            title  = name,
                            url    = self.fix_url(slug),
                            poster = self.fix_url(poster)
                        ))
                return results

        return []

    async def load_item(self, url: str) -> SeriesInfo | MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_direct_text("h1")
        poster_attr = secici.select_attr("img.series-profile-thumb", "data-srcset") or secici.select_attr("img.series-profile-thumb", "srcset")
        if poster_attr:
            # "url 1x, url 2x" -> en sondakini (en yüksek kalite) al
            poster = poster_attr.split(",")[-1].strip().split(" ")[0]
        else:
            poster = secici.select_poster("img.series-profile-thumb")

        description = secici.select_text("p#tv-series-desc")
        tags        = secici.select_texts("div.item.categories a")
        rating      = secici.select_text("span.color-imdb")
        actors      = secici.select_texts("div.content h5")
        year        = secici.extract_year("div.truncate")
        duration    = secici.regex_first(r"(\d+)", secici.select_text(".media-meta td:last-child"))
        if duration == year or int(duration) < 40:
            duration = None

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

        episodes = []
        for tab in secici.select("div.ui.tab"):
            for link in secici.select("a[href*='bolum']", tab):
                href = link.attrs.get("href")
                if href:
                    s, e = secici.extract_season_episode(href)
                    name = secici.select_text("div.content div.header", link) or link.text(strip=True)
                    episodes.append(Episode(season=s or 1, episode=e or 1, title=name, url=self.fix_url(href)))

        if episodes:
            return SeriesInfo(**common_info, episodes=episodes)

        return MovieInfo(**common_info)

    def _find_iframe(self, secici: HTMLHelper) -> str | None:
        """Sayfa kaynağındaki video iframe adresini bulur."""
        src = secici.select_attr("iframe", "src") or \
              secici.select_attr("iframe", "data-src") or \
              secici.regex_first(r'<iframe[^>]+src="([^"]+)"')
        return self.fix_url(src) if src else None

    async def _process_source(self, source: dict, subtitles: list) -> list[ExtractResult]:
        """Tekil bir kaynağı işleyip sonucu döndürür."""
        target_url = source["url"]
        name       = source["name"]

        # Eğer direkt iframe değilse (Sayfa linki ise), önce iframe'i bul
        if not source.get("is_main"):
            try:
                resp     = await self.httpx.get(target_url)
                temp_sel = HTMLHelper(resp.text)

                if not (iframe_url := self._find_iframe(temp_sel)):
                    return []

                target_url = iframe_url

                # Tab (Dil Seçeneği) ise, gittiğimiz sayfadaki aktif player ismini ekle
                if source.get("is_tab"):
                    p_name = temp_sel.select_text("div.alternatives-for-this div.playeritems.active") or "PUB"
                    name   = f"{name} | {p_name}"
            except Exception:
                return []

        # Linki Extract Et
        try:
            extracted = await self.extract(target_url, referer=self.main_url)
            if not extracted:
                return []

            items = extracted if isinstance(extracted, list) else [extracted]

            # Sonuçları işle (İsim ver, altyazı ekle)
            copy_subtitles = list(subtitles) # Her item için kopyasını kullan
            for item in items:
                item.name = name
                if copy_subtitles:
                    if not item.subtitles:
                        item.subtitles = copy_subtitles
                    else:
                        item.subtitles.extend(copy_subtitles)

            return items
        except Exception:
            return []

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        # 1. Altyazıları Topla
        subtitles = []
        for track in secici.select("track"):
            if track.attrs.get("kind") in ("subtitles", "captions"):
                if src := track.attrs.get("src"):
                    lang = track.attrs.get("label") or track.attrs.get("srclang") or "Altyazı"
                    subtitles.append(self.new_subtitle(src, lang))

        sources = []

        # Aktif Sayfa Bilgileri
        active_tab_name = secici.select_text("div#series-tabs a.active") or "Sinefy"
        active_player   = secici.select_text("div.alternatives-for-this div.playeritems.active") or "PUB"

        # A) Ana Video (Main Iframe)
        if main_iframe := self._find_iframe(secici):
            sources.append({
                "url"     : main_iframe,
                "name"    : f"{active_tab_name} | {active_player}",
                "is_main" : True,
                "is_tab"  : False
            })

        # B) Alternatif Playerlar (Mevcut Sayfa Player Butonları)
        for btn in secici.select("div.alternatives-for-this div.playeritems:not(.active) a"):
            if href := btn.attrs.get("href"):
                if "javascript" not in href:
                    sources.append({
                        "url"     : self.fix_url(href),
                        "name"    : f"{active_tab_name} | {btn.text(strip=True)}",
                        "is_main" : False,
                        "is_tab"  : False
                    })

        # C) Diğer Dil Seçenekleri (Tabs - Sekmeler)
        for tab in secici.select("div#series-tabs a:not(.active)"):
            if href := tab.attrs.get("href"):
                sources.append({
                    "url"     : self.fix_url(href),
                    "name"    : tab.text(strip=True),
                    "is_main" : False,
                    "is_tab"  : True
                })

        # 2. Kaynakları Paralel İşle
        tasks = [self._process_source(src, subtitles) for src in sources]
        results_groups = await asyncio.gather(*tasks)

        # 3. Sonuçları Birleştir
        final_results = []
        for group in results_groups:
             if group:
                final_results.extend(group)

        # 4. Duplicate Temizle (URL + İsim Kombinasyonu)
        unique_results = []
        seen = set()
        for res in final_results:
            key = (res.url, res.name)
            if res.url and key not in seen:
                unique_results.append(res)
                seen.add(key)

        return unique_results
