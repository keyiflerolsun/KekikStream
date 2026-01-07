# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult
from selectolax.parser import HTMLParser
import re

class FilmMakinesi(PluginBase):
    name        = "FilmMakinesi"
    language    = "tr"
    main_url    = "https://filmmakinesi.to"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Film Makinesi ile en yeni ve güncel filmleri Full HD kalite farkı ile izleyebilirsiniz. Film izle denildiğinde akla gelen en kaliteli film sitesi."

    main_page   = {
        f"{main_url}/filmler-1/"                : "Son Filmler",
        f"{main_url}/tur/aksiyon-fm1/film/"     : "Aksiyon",
        f"{main_url}/tur/aile-fm1/film/"        : "Aile",
        f"{main_url}/tur/animasyon-fm2/film/"   : "Animasyon",
        f"{main_url}/tur/belgesel/film/"        : "Belgesel",
        f"{main_url}/tur/biyografi/film/"       : "Biyografi",
        f"{main_url}/tur/bilim-kurgu-fm3/film/" : "Bilim Kurgu",
        f"{main_url}/tur/dram-fm1/film/"        : "Dram",
        f"{main_url}/tur/fantastik-fm1/film/"   : "Fantastik",
        f"{main_url}/tur/gerilim-fm1/film/"     : "Gerilim",
        f"{main_url}/tur/gizem/film/"           : "Gizem",
        f"{main_url}/tur/komedi-fm1/film/"      : "Komedi",
        f"{main_url}/tur/korku-fm1/film/"       : "Korku",
        f"{main_url}/tur/macera-fm1/film/"      : "Macera",
        f"{main_url}/tur/muzik/film/"           : "Müzik",
        f"{main_url}/tur/polisiye/film/"        : "Polisiye",
        f"{main_url}/tur/romantik-fm1/film/"    : "Romantik",
        f"{main_url}/tur/savas-fm1/film/"       : "Savaş",
        f"{main_url}/tur/spor/film/"            : "Spor",
        f"{main_url}/tur/tarih/film/"           : "Tarih",
        f"{main_url}/tur/western-fm1/film/"     : "Western"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = self.cloudscraper.get(f"{url}{'' if page == 1 else f'page/{page}/'}")
        secici = HTMLParser(istek.text)

        results = []
        for veri in secici.css("div.item-relative"):
            title_el = veri.css_first("div.title")
            link_el  = veri.css_first("a")
            img_el   = veri.css_first("img")

            title  = title_el.text(strip=True) if title_el else None
            href   = link_el.attrs.get("href") if link_el else None
            poster = (img_el.attrs.get("data-src") or img_el.attrs.get("src")) if img_el else None

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster) if poster else None,
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/arama/?s={query}")
        secici = HTMLParser(istek.text)

        results = []
        for article in secici.css("div.item-relative"):
            title_el = article.css_first("div.title")
            link_el  = article.css_first("a")
            img_el   = article.css_first("img")

            title  = title_el.text(strip=True) if title_el else None
            href   = link_el.attrs.get("href") if link_el else None
            poster = (img_el.attrs.get("data-src") or img_el.attrs.get("src")) if img_el else None

            if title and href:
                results.append(SearchResult(
                    title  = title.strip(),
                    url    = self.fix_url(href.strip()),
                    poster = self.fix_url(poster.strip()) if poster else None,
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)

        title_el = secici.css_first("h1.title")
        title    = title_el.text(strip=True) if title_el else ""

        poster_el = secici.css_first("img.cover-img")
        poster    = poster_el.attrs.get("src", "").strip() if poster_el else ""

        desc_el     = secici.css_first("div.info-description p")
        description = desc_el.text(strip=True) if desc_el else ""

        rating_el = secici.css_first("div.score")
        rating    = None
        if rating_el:
            rating_text = rating_el.text(strip=True)
            if rating_text:
                rating = rating_text.split()[0]

        year_el = secici.css_first("span.date a")
        year    = year_el.text(strip=True) if year_el else ""

        actors = [el.text(strip=True) for el in secici.css("div.cast-name") if el.text(strip=True)]
        tags   = [el.text(strip=True) for el in secici.css("div.genre a") if el.text(strip=True)]

        duration_el = secici.css_first("div.time")
        duration    = None
        if duration_el:
            duration_text = duration_el.text(strip=True)
            parts = duration_text.split()
            if len(parts) > 1:
                duration = parts[1].strip()

        # Dizi mi kontrol et - sezon/bölüm linkleri var mı?
        episodes = []
        all_links = secici.css("a[href]")
        for link in all_links:
            href = link.attrs.get("href", "")
            match = re.search(r"/sezon-(\d+)/bolum-(\d+)", href)
            if match:
                season_no = int(match.group(1))
                ep_no = int(match.group(2))
                
                # Bölüm başlığını çıkar - text'ten gerçek ismi al
                # Format: "22 Eylül 2014 / 44 dk /1. Sezon / 1. BölümPilot"
                full_text = link.text(strip=True)
                # "Bölüm" kelimesinden sonraki kısmı al
                ep_title = ""
                if "Bölüm" in full_text:
                    parts = full_text.split("Bölüm")
                    if len(parts) > 1:
                        ep_title = parts[-1].strip()
                
                episodes.append(Episode(
                    season  = season_no,
                    episode = ep_no,
                    title   = ep_title,
                    url     = self.fix_url(href)
                ))
        
        # Bölümler varsa SeriesInfo döndür
        if episodes:
            # Tekrar eden bölümleri kaldır
            seen = set()
            unique_episodes = []
            for ep in episodes:
                key = (ep.season, ep.episode)
                if key not in seen:
                    seen.add(key)
                    unique_episodes.append(ep)
            
            # Sırala
            unique_episodes.sort(key=lambda x: (x.season or 0, x.episode or 0))
            
            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster) if poster else None,
                title       = self.clean_title(title),
                description = description,
                tags        = tags,
                rating      = rating,
                year        = year,
                actors      = actors,
                duration    = duration,
                episodes    = unique_episodes
            )

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster) if poster else None,
            title       = self.clean_title(title),
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors,
            duration    = duration
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)

        response = []

        # Video parts linklerini ve etiketlerini al
        for link in secici.css("div.video-parts a[data-video_url]"):
            video_url = link.attrs.get("data-video_url")
            label     = link.text(strip=True) if link.text(strip=True) else ""

            if video_url:
                data = await self.extract(video_url, prefix=label.split()[0] if label else None)
                if data:
                    response.append(data)

        # Eğer video-parts yoksa iframe kullan
        if not response:
            iframe_el = secici.css_first("iframe")
            iframe_src = iframe_el.attrs.get("data-src") if iframe_el else None
            if iframe_src:
                data = await self.extract(iframe_src)
                if data:
                    response.append(data)

        return response
