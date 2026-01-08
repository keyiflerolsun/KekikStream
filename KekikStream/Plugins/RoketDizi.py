# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, MovieInfo, HTMLHelper
import base64, json

class RoketDizi(PluginBase):
    name        = "RoketDizi"
    lang        = "tr"
    main_url    = "https://roketdizi.to"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Türkiye'nin en tatlış yabancı dizi izleme sitesi. Türkçe dublaj, altyazılı, eski ve yeni yabancı dizilerin yanı sıra kore (asya) dizileri izleyebilirsiniz."

    main_page = {
       f"{main_url}/dizi/tur/aksiyon"     : "Aksiyon",
       f"{main_url}/dizi/tur/bilim-kurgu" : "Bilim Kurgu",
       f"{main_url}/dizi/tur/gerilim"     : "Gerilim",
       f"{main_url}/dizi/tur/fantastik"   : "Fantastik",
       f"{main_url}/dizi/tur/komedi"      : "Komedi",
       f"{main_url}/dizi/tur/korku"       : "Korku",
       f"{main_url}/dizi/tur/macera"      : "Macera",
       f"{main_url}/dizi/tur/suc"         : "Suç"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}?&page={page}")
        secici = HTMLHelper(istek.text)

        results = []

        # Use div.new-added-list to find the container, then get items
        for item in secici.select("div.new-added-list > span"):
            title  = secici.select_text("span.line-clamp-1", item)
            href   = secici.select_attr("a", "href", item)
            poster = secici.select_attr("img", "src", item)

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = self.clean_title(title),
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster) if poster else None
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek = await self.httpx.post(
            url     = f"{self.main_url}/api/bg/searchContent?searchterm={query}",
            headers = {
                "Accept"           : "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With" : "XMLHttpRequest",
                "Referer"          : f"{self.main_url}/",
            }
        )
        
        try:
            veri    = istek.json()
            encoded = veri.get("response", "")
            if not encoded:
                return []

            decoded = base64.b64decode(encoded).decode("utf-8")
            veri    = json.loads(decoded)

            if not veri.get("state"):
                return []

            results = []

            for item in veri.get("result", []):
                title  = item.get("object_name", "")
                slug   = item.get("used_slug", "")
                poster = item.get("object_poster_url", "")

                if title and slug:
                    results.append(SearchResult(
                        title  = self.clean_title(title.strip()),
                        url    = self.fix_url(f"{self.main_url}/{slug}"),
                        poster = self.fix_url(poster) if poster else None
                    ))

            return results

        except Exception:
            return []

    async def load_item(self, url: str) -> SeriesInfo:
        # Note: Handling both Movie and Series logic in one, returning SeriesInfo generally or MovieInfo
        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)
        html_text = resp.text

        title    = sel.select_text("h1.text-white")

        poster    = sel.select_attr("div.w-full.page-top img", "src")

        description = sel.select_text("div.mt-2.text-sm")

        # Tags - genre bilgileri (Detaylar bölümünde)
        tags = []
        genre_text = sel.select_text("h3.text-white.opacity-90")
        if genre_text:
            tags = [t.strip() for t in genre_text.split(",")]

        # Rating
        rating    = sel.select_text("span.text-white.text-sm.font-bold")

        # Year ve Actors - Detaylar (Details) bölümünden
        year = None
        actors = []

        # Detaylar bölümündeki tüm flex-col div'leri al
        detail_items = sel.select("div.flex.flex-col")
        for item in detail_items:
            label = sel.select_text("span.text-base", item)
            value = sel.select_text("span.text-sm.opacity-90", item)
            
            label = label if label else None
            value = value if value else None
            
            if label and value:
                # Yayın tarihi (yıl)
                if label == "Yayın tarihi":
                    # "16 Ekim 2018" formatından yılı çıkar
                    year = HTMLHelper(value).regex_first(r'\d{4}')
                # Yaratıcılar veya Oyuncular
                elif label in ["Yaratıcılar", "Oyuncular"]:
                    if value:
                        actors.append(value)

        # Check urls for episodes
        all_urls = HTMLHelper(html_text).regex_all(r'"url":"([^"]*)"')
        is_series = any("bolum-" in u for u in all_urls)

        episodes = []
        if is_series:
            # Dict kullanarak duplicate'leri önle ama sıralı tut
            episodes_dict = {}
            for u in all_urls:
                if "bolum" in u and u not in episodes_dict:
                    season = HTMLHelper(u).regex_first(r'/sezon-(\d+)')
                    ep_num = HTMLHelper(u).regex_first(r'/bolum-(\d+)')

                    season = int(season) if season else 1
                    episode_num = int(ep_num) if ep_num else 1

                    # Key olarak (season, episode) tuple kullan
                    key = (season, episode_num)
                    episodes_dict[key] = Episode(
                        season  = season,
                        episode = episode_num,
                        title   = f"{season}. Sezon {episode_num}. Bölüm",
                        url     = self.fix_url(u)
                    )

            # Sıralı liste oluştur
            episodes = [episodes_dict[key] for key in sorted(episodes_dict.keys())]

        return SeriesInfo(
            title       = title,
            url         = url,
            poster      = self.fix_url(poster) if poster else None,
            description = description,
            tags        = tags,
            rating      = rating,
            actors      = actors,
            episodes    = episodes,
            year        = year
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)
        
        next_data = sel.select_text("script#__NEXT_DATA__")
        if not next_data:
            return []

        try:
            data = json.loads(next_data)
            secure_data = data["props"]["pageProps"]["secureData"]
            decoded_json = json.loads(base64.b64decode(secure_data).decode('utf-8'))

            # secureData içindeki RelatedResults -> getEpisodeSources -> result dizisini al
            sources = decoded_json.get("RelatedResults", {}).get("getEpisodeSources", {}).get("result", [])

            seen_urls = set()
            results = []
            for source in sources:
                source_content = source.get("source_content", "")

                # iframe URL'ini source_content'ten çıkar
                iframe_url = HTMLHelper(source_content).regex_first(r'<iframe[^>]*src=["\']([^"\']*)["\']')
                if not iframe_url:
                    continue
                
                # Fix URL protocol
                if not iframe_url.startswith("http"):
                    if iframe_url.startswith("//"):
                        iframe_url = "https:" + iframe_url
                    else:
                        iframe_url = "https://" + iframe_url

                iframe_url = self.fix_url(iframe_url)
                
                # Deduplicate  
                if iframe_url in seen_urls:
                    continue
                seen_urls.add(iframe_url)

                # Extract with helper
                data = await self.extract(iframe_url)
                if data:
                    results.append(data)

            return results

        except Exception:
            return []
