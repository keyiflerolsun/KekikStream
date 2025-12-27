# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, MovieInfo
from selectolax.parser import HTMLParser
import re, base64, json

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
        secici = HTMLParser(istek.text)

        results = []

        # Use div.new-added-list to find the container, then get items
        for item in secici.css("div.new-added-list > span"):
            title_el = item.css_first("span.line-clamp-1")
            link_el  = item.css_first("a")
            img_el   = item.css_first("img")

            title  = title_el.text(strip=True) if title_el else None
            href   = link_el.attrs.get("href") if link_el else None
            poster = img_el.attrs.get("src") if img_el else None

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
        sel  = HTMLParser(resp.text)
        html_text = resp.text

        title_el = sel.css_first("h1.text-white")
        title    = title_el.text(strip=True) if title_el else None

        poster_el = sel.css_first("div.w-full.page-top img")
        poster    = poster_el.attrs.get("src") if poster_el else None

        desc_el     = sel.css_first("div.mt-2.text-sm")
        description = desc_el.text(strip=True) if desc_el else None

        # Tags - genre bilgileri (Detaylar bölümünde)
        tags = []
        genre_el = sel.css_first("h3.text-white.opacity-90")
        if genre_el:
            genre_text = genre_el.text(strip=True)
            if genre_text:
                tags = [t.strip() for t in genre_text.split(",")]

        # Rating
        rating_el = sel.css_first("span.text-white.text-sm.font-bold")
        rating    = rating_el.text(strip=True) if rating_el else None

        # Year ve Actors - Detaylar (Details) bölümünden
        year = None
        actors = []

        # Detaylar bölümündeki tüm flex-col div'leri al
        detail_items = sel.css("div.flex.flex-col")
        for item in detail_items:
            label_el = item.css_first("span.text-base")
            value_el = item.css_first("span.text-sm.opacity-90")
            
            label = label_el.text(strip=True) if label_el else None
            value = value_el.text(strip=True) if value_el else None
            
            if label and value:
                # Yayın tarihi (yıl)
                if label == "Yayın tarihi":
                    # "16 Ekim 2018" formatından yılı çıkar
                    year_match = re.search(r'\d{4}', value)
                    if year_match:
                        year = year_match.group()
                
                # Yaratıcılar veya Oyuncular
                elif label in ["Yaratıcılar", "Oyuncular"]:
                    if value:
                        actors.append(value)

        # Check urls for episodes
        all_urls = re.findall(r'"url":"([^"]*)"', html_text)
        is_series = any("bolum-" in u for u in all_urls)

        episodes = []
        if is_series:
            # Dict kullanarak duplicate'leri önle ama sıralı tut
            episodes_dict = {}
            for u in all_urls:
                if "bolum" in u and u not in episodes_dict:
                    season_match = re.search(r'/sezon-(\d+)', u)
                    ep_match     = re.search(r'/bolum-(\d+)', u)

                    season = int(season_match.group(1)) if season_match else 1
                    episode_num = int(ep_match.group(1)) if ep_match else 1

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
        sel  = HTMLParser(resp.text)
        
        next_data_el = sel.css_first("script#__NEXT_DATA__")
        if not next_data_el:
            return []

        next_data = next_data_el.text(strip=True)
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
                iframe_match = re.search(r'<iframe[^>]*src=["\']([^"\']*)["\']', source_content)
                if not iframe_match:
                    continue

                iframe_url = iframe_match.group(1)
                
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
