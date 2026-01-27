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
                    poster   = self.fix_url(poster)
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
                        poster = self.fix_url(poster)
                    ))

            return results

        except Exception:
            return []

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)
        
        next_data_text = sel.select_text("script#__NEXT_DATA__")
        if not next_data_text:
            return SeriesInfo(url=url, title=sel.select_text("h1") or "Bilinmeyen")

        try:
            next_data = json.loads(next_data_text)
            secure_data_raw = next_data["props"]["pageProps"]["secureData"]
            secure_data = json.loads(base64.b64decode(secure_data_raw).decode('utf-8'))
            
            content_item = secure_data.get("contentItem", {})
            content      = secure_data.get("content", {}).get("result", {})
            
            title       = content_item.get("original_title") or content_item.get("culture_title")
            poster      = content_item.get("poster_url") or content_item.get("face_url")
            description = content_item.get("description")
            rating      = str(content_item.get("imdb_point") or "")
            year        = str(content_item.get("release_year") or "")
            tags        = content_item.get("categories", "").split(",")
            
            # Actors extraction from getSerieCastsById or getMovieCastsById
            actors = []
            casts_data = content.get("getSerieCastsById") or content.get("getMovieCastsById")
            if casts_data and casts_data.get("result"):
                actors = [cast.get("name") for cast in casts_data["result"] if cast.get("name")]

            # Episodes extraction
            episodes = []
            if "Series" in str(content.get("FindedType")):
                # Check for episodes in SecureData -> RelatedResults -> getEpisodeSources (this might be for the current episode)
                # Usually full episode list isn't in secureData, but we can get it from HTML or another API
                # However, many times Next.js pages have them in props
                # Let's fallback to the previous regex method for episodes if not in JSON
                all_urls = HTMLHelper(resp.text).regex_all(r'"url":"([^"]*)"')
                episodes_dict = {}
                for u in all_urls:
                    if "bolum" in u and u not in episodes_dict:
                        s_match = HTMLHelper(u).regex_first(r'/sezon-(\d+)')
                        e_match = HTMLHelper(u).regex_first(r'/bolum-(\d+)')
                        s_val = int(s_match) if s_match else 1
                        e_val = int(e_match) if e_match else 1
                        episodes_dict[(s_val, e_val)] = Episode(
                            season  = s_val,
                            episode = e_val,
                            title   = f"{s_val}. Sezon {e_val}. Bölüm",
                            url     = self.fix_url(u)
                        )
                episodes = [episodes_dict[key] for key in sorted(episodes_dict.keys())]

                return SeriesInfo(
                    url         = url,
                    poster      = self.fix_url(poster),
                    title       = self.clean_title(title),
                    description = description,
                    tags        = tags,
                    rating      = rating,
                    year        = year,
                    actors      = actors,
                    episodes    = episodes
                )
            else:
                return MovieInfo(
                    url         = url,
                    poster      = self.fix_url(poster),
                    title       = self.clean_title(title),
                    description = description,
                    tags        = tags,
                    rating      = rating,
                    year        = year,
                    actors      = actors
                )

        except Exception:
            # Fallback to simple extraction if JSON parsing fails
            return SeriesInfo(
                url   = url,
                title = self.clean_title(sel.select_text("h1")) or "Bilinmeyen"
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
