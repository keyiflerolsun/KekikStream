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

        title       = self.clean_title(helper.select_text("h1"))
        poster      = helper.select_poster(".poster img")
        description = helper.select_text(".excerpt p")
        year        = helper.extract_year(".release", ".movie-info")
        rating      = helper.regex_first(r"([\d\.]+)", helper.select_text(".imdb-rating"))
        duration    = int(helper.regex_first(r"(\d+)", helper.select_text(".movie-info")) or 0)
        tags        = helper.select_texts("a[href*='/tur/'], a[href*='/Kategori/tur/']")
        actors      = helper.select_texts("a[href*='/oyuncular/']") or helper.select_texts(".cast-list .actor-name, .cast-list a")

        # Bölüm linklerini kontrol et
        ep_elements = helper.select(".parts-middle a, .parts-middle .part.active")

        if not ep_elements:
            return MovieInfo(
                url         = url,
                title       = title,
                description = description,
                poster      = self.fix_url(poster),
                year        = year,
                rating      = rating,
                duration    = duration,
                tags        = tags,
                actors      = actors
            )
        
        episodes = []
        for i, el in enumerate(ep_elements):
            name = helper.select_text(".part-name", el) or f"Bölüm {i+1}"
            href = el.attrs.get("href") or url
            s, e = helper.extract_season_episode(name)
            episodes.append(Episode(season=s or 1, episode=e or (i + 1), title=name, url=self.fix_url(href)))

        return SeriesInfo(
            url         = url,
            title       = title,
            description = description,
            poster      = self.fix_url(poster),
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
