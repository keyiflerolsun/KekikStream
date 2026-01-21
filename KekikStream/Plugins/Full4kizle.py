# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re

class Full4kizle(PluginBase):
    name        = "Full4kizle"
    language    = "tr"
    main_url    = "https://izlehdfilm.cc"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Filmci Baba, film izleme sitesi 4k Full film izle, 1080p ve 4k kalite de sinema filmleri ve dizileri, tek parça hd kalitede türkçe dublajlı filmler seyret."

    main_page = {
        f"{main_url}/Kategori/en-populer-filmler/page"        : "En Popüler Filmler",
        f"{main_url}/Kategori/vizyondaki-filmler-izle/page"   : "Vizyondaki Filmler",
        f"{main_url}/Kategori/yerli-filmler-izle/page"        : "Yerli Filmler",
        f"{main_url}/Kategori/yabanci-diziler/page"           : "Yabancı Diziler",
        f"{main_url}/Kategori/netflix-filmleri-izle/page"     : "Netflix Filmleri",
        f"{main_url}/Kategori/netflix-dizileri/page"          : "Netflix Dizileri",
        f"{main_url}/Kategori/anime-izle/page"                : "Anime İzle",
        f"{main_url}/Kategori/cizgi-filmler/page"             : "Çizgi Filmler",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        target_url = f"{url}/{page}/"
        istek = await self.httpx.get(target_url)
        helper = HTMLHelper(istek.text)
        
        items = helper.select("div.movie-preview")
        results = []
        
        for item in items:
            title_el = helper.select_first(".movie-title a", item)
            if not title_el: continue
            
            title = title_el.text(strip=True)
            # Remove " izle" case insensitive
            title = re.sub(r"(?i) izle", "", title).strip()
            
            href = self.fix_url(title_el.attrs.get("href"))
            
            poster_el = helper.select_first(".movie-poster img", item)
            poster = self.fix_url(poster_el.attrs.get("src")) if poster_el else None
            
            results.append(MainPageResult(
                category = category,
                title    = title,
                url      = href,
                poster   = poster
            ))
            
        return results

    async def search(self, query: str) -> list[SearchResult]:
        url = f"{self.main_url}/?s={query}"
        istek = await self.httpx.get(url)
        helper = HTMLHelper(istek.text)
        
        items = helper.select("div.movie-preview")
        results = []
        
        for item in items:
            title_el = helper.select_first(".movie-title a", item)
            if not title_el: continue
            
            title = title_el.text(strip=True)
            # Remove " izle" case insensitive
            title = re.sub(r"(?i) izle", "", title).strip()
            
            href = self.fix_url(title_el.attrs.get("href"))
            
            poster_el = helper.select_first(".movie-poster img", item)
            poster = self.fix_url(poster_el.attrs.get("src")) if poster_el else None
            
            results.append(SearchResult(
                title  = title,
                url    = href,
                poster = poster
            ))
            
        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek = await self.httpx.get(url)
        helper = HTMLHelper(istek.text)
        
        title_raw = helper.select_text("h1") or "Bilinmiyor"
        title = re.sub(r"(?i)izle", "", title_raw).strip()
        
        poster_el = helper.select_first(".poster img")
        poster = self.fix_url(poster_el.attrs.get("src")) if poster_el else None
        
        description = helper.select_text(".excerpt p")
        
        year_text = helper.select_text(".release a")
        year = year_text.strip() if year_text else None
        
        rating_text = helper.select_text(".imdb-rating")
        rating = None
        if rating_text:
            rating_text = rating_text.replace("IMDB Puanı", "").strip()
            rating = rating_text
            
        # Check for Episodes to decide if Series or Movie
        ep_elements = helper.select(".parts-middle a, .parts-middle .part.active")
        
        if not ep_elements:
            # Movie
            return MovieInfo(
                url         = url,
                title       = title,
                description = description,
                poster      = poster,
                year        = year,
                rating      = rating,
                tags        = None, # Tags usually in genres list, implementation skipped for now or add if easy
                actors      = None  # Actors not extracted in Kotlin reference provided
            )
        else:
            # Series
            episodes = []
            for i, el in enumerate(ep_elements):
                ep_name = helper.select_text(".part-name", el) or f"Bölüm {i+1}"
                ep_href = el.attrs.get("href")
                if not ep_href:
                    ep_href = url # Current page if href is empty/active?
                ep_href = self.fix_url(ep_href)
                
                # Parse season/episode from name if possible
                # Kotlin: find digit for season, substringAfter("Sezon") digit for episode
                season = 1
                episode = i + 1
                
                # Simple heuristic similar to Kotlin
                # "1. Sezon 5. Bölüm"
                s_match = re.search(r"(\d+)\.\s*Sezon", ep_name)
                e_match = re.search(r"(\d+)\.\s*Bölüm", ep_name)
                
                if s_match:
                    season = int(s_match.group(1))
                if e_match:
                    episode = int(e_match.group(1))
                    
                episodes.append(Episode(
                    season  = season,
                    episode = episode,
                    title   = ep_name,
                    url     = ep_href
                ))
                
            return SeriesInfo(
                url         = url,
                title       = title,
                description = description,
                poster      = poster,
                year        = year,
                rating      = rating,
                tags        = None,
                actors      = None,
                episodes    = episodes
            )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek = await self.httpx.get(url)
        helper = HTMLHelper(istek.text)
        
        iframe = helper.select_attr(".center-container iframe", "src")
        if not iframe:
            iframe = helper.select_attr("iframe[src*='hotstream.club']", "src")
            
        results = []
        
        if iframe:
            iframe = self.fix_url(iframe)
            
            # Use general extract method
            extracted = await self.extract(iframe)
            if extracted:
                if isinstance(extracted, list):
                    results.extend(extracted)
                else:
                    results.append(extracted)
            else:
                 results.append(ExtractResult(
                    name = "Full4kizle | External",
                    url  = iframe,
                    referer = url
                ))
                
        return results
