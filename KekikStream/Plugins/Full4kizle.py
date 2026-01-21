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
        f"{main_url}/Kategori/en-populer-filmler/page"              : "En Popüler Filmler",
        f"{main_url}/Kategori/tur/aksiyon-filmleri/page"            : "Aksiyon",
        f"{main_url}/Kategori/tur/macera-filmleri/page"             : "Macera",
        f"{main_url}/Kategori/tur/bilim-kurgu-filmleri/page"        : "Bilim Kurgu",
        f"{main_url}/Kategori/tur/fantastik-filmler/page"           : "Fantastik",
        f"{main_url}/Kategori/tur/korku-filmleri/page"              : "Korku",
        f"{main_url}/Kategori/tur/gerilim-filmleri-hd/page"         : "Gerilim",
        f"{main_url}/Kategori/tur/gizem-filmleri/page"              : "Gizem",
        f"{main_url}/Kategori/tur/dram-filmleri-hd/page"            : "Dram",
        f"{main_url}/Kategori/tur/komedi-filmleri-hd/page"          : "Komedi",
        f"{main_url}/Kategori/tur/romantik-filmler/page"            : "Romantik",
        f"{main_url}/Kategori/tur/aile-filmleri/page"               : "Aile",
        f"{main_url}/Kategori/tur/animasyon-filmleri/page"          : "Animasyon",
        f"{main_url}/Kategori/tur/biyografi-filmleri/page"          : "Biyografi",
        f"{main_url}/Kategori/tur/polisiye-suc-filmleri/page"       : "Polisiye / Suç",
        f"{main_url}/Kategori/tur/savas-filmleri/page"              : "Savaş",
        f"{main_url}/Kategori/tur/western-filmler/page"             : "Western",
        f"{main_url}/Kategori/tur/hint-filmleri/page"               : "Hint Filmleri",
        f"{main_url}/Kategori/tur/kore-filmleri/page"               : "Kore Filmleri",
        f"{main_url}/Kategori/tur/yerli-filmler-izle/page"          : "Yerli Filmler",
        f"{main_url}/Kategori/tur/yerli-diziler/page"               : "Yerli Diziler",
        f"{main_url}/Kategori/tur/18-erotik-filmler/page"           : "+18 Erotik Filmler",
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
        
        # Robust metadata extraction using Regex
        
        # Initialize year first
        year = None
        
        # Try .release first (legacy) or directly regex
        rel_text = helper.select_text(".release")
        if rel_text:
             m_y = re.search(r"(\d{4})", rel_text)
             if m_y: year = m_y.group(1)
             
        # Year fallbacks
        if not year:
            # Try finding year in text like "Yapım: 2024" or just isolated year in release date
            m_year = helper.regex_first(r"Yapım:\s*(\d{4})") or helper.regex_first(r"Yıl:\s*(\d{4})")
            if m_year:
                year = m_year

        # Rating
        rating_text = helper.select_text(".imdb-rating")
        if rating_text:
            rating = rating_text.replace("IMDB Puanı", "").strip()
        else:
            rating = helper.regex_first(r"IMDB\s*:\s*([\d\.]+)")

        # Duration
        duration = None
        duration_val = helper.regex_first(r"Süre:\s*(\d+)")
        if duration_val:
            duration = int(duration_val)

        # Actors - Extract from actor links
        actors = None
        actors_list = []
        
        # Site uses: <a href=".../oyuncular/...">Actor Name</a>
        actor_els = helper.select("a[href*='/oyuncular/']")
        if actor_els:
            actors_list = [el.text(strip=True) for el in actor_els if el.text(strip=True)]
        
        # Fallback: Try .cast-list selector
        if not actors_list:
            actor_els = helper.select(".cast-list .actor-name, .cast-list a")
            if actor_els:
                actors_list = [el.text(strip=True) for el in actor_els if el.text(strip=True)]
        
        if actors_list:
            actors = ", ".join(actors_list)


        # Tags (Genres) - Extract from genre links
        tags = None
        tags_list = []
        
        # Site uses: <a href=".../tur/...">Genre Name</a> or <a href=".../Kategori/tur/...">
        tag_els = helper.select("a[href*='/tur/'], a[href*='/Kategori/tur/']")
        if tag_els:
            tags_list = [el.text(strip=True) for el in tag_els if el.text(strip=True)]
        
        # Fallback: Try .genres selector
        if not tags_list:
            tag_els = helper.select(".genres a, .genre a")
            if tag_els:
                tags_list = [el.text(strip=True) for el in tag_els if el.text(strip=True)]
        
        # Remove duplicates while preserving order
        if tags_list:
            seen = set()
            unique_tags = []
            for tag in tags_list:
                if tag not in seen:
                    seen.add(tag)
                    unique_tags.append(tag)
            tags = unique_tags if unique_tags else None

            
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
                duration    = duration,
                tags        = tags,
                actors      = actors
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
                duration    = duration,
                tags        = tags,
                actors      = actors,
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
