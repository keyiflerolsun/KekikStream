# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper
import re

class FilmCenneti(PluginBase):
    name        = "FilmCenneti"
    language    = "tr"
    main_url    = "https://filmcenneti.org"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "En yeni ve popüler Türk filmlerini Full HD ve ücretsiz izle! Kesintisiz film keyfi için hemen Filmsaati.tv'yi ziyaret et ve HD kalitesinde sinema keyfini yaşa!"

    main_page   = {
        f"{main_url}/aile-filmleri"        : "Aile",
        f"{main_url}/aksiyon-filmleri"     : "Aksiyon",
        f"{main_url}/animasyon-filmleri"   : "Animasyon",
        f"{main_url}/belgesel-filmleri"    : "Belgesel",
        f"{main_url}/bilim-kurgu-filmleri" : "Bilim-Kurgu",
        f"{main_url}/biyografi-filmleri"   : "Biyografi",
        f"{main_url}/diziler"              : "Diziler",
        f"{main_url}/dram-filmleri"        : "Dram",
        f"{main_url}/fantastik-filmleri"   : "Fantastik",
        f"{main_url}/gerilim-filmleri"     : "Gerilim",
        f"{main_url}/gizem-filmleri"       : "Gizem",
        f"{main_url}/komedi-filmleri"      : "Komedi",
        f"{main_url}/korku-filmleri"       : "Korku",
        f"{main_url}/macera-filmleri"      : "Macera",
        f"{main_url}/muzik-filmleri"       : "Müzik",
        f"{main_url}/romantik-filmleri"    : "Romantik",
        f"{main_url}/sava-filmleri"        : "Savaş",
        f"{main_url}/suc-filmleri"         : "Suç",
        f"{main_url}/tarih-filmleri"       : "Tarih",
        f"{main_url}/western-filmleri"     : "Western",
    }

    async def get_articles(self, secici: HTMLHelper) -> list[dict]:
        articles = []

        # New design: div.th-item
        items = secici.select("div.th-item")
        if not items:
            # Fallback to old design
            items = secici.select("article.movie-box")

        for veri in items:
            title_el = veri.select_first("a")
            if not title_el:
                continue

            title  = title_el.attrs.get("title") or title_el.select_text(".th-title") or title_el.text(strip=True)
            href   = title_el.attrs.get("href")
            poster = veri.select_poster("img")

            if title and href:
                # Clean title of any ending year like " (2026)"
                if title.endswith(")") and "(" in title:
                    title = title.split("(")[0].strip()
                articles.append({
                    "title"  : title,
                    "url"    : self.fix_url(href),
                    "poster" : self.fix_url(poster),
                })

        return articles

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        if page > 1:
            req_url = f"{url.rstrip('/')}/page/{page}/"
        else:
            req_url = url

        istek   = await self.httpx.get(req_url)
        secici  = HTMLHelper(istek.text)
        veriler = await self.get_articles(secici)

        return [MainPageResult(**veri, category=category) for veri in veriler if veri]

    async def search(self, query: str) -> list[SearchResult]:
        istek   = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici  = HTMLHelper(istek.text)
        veriler = await self.get_articles(secici)

        return [SearchResult(**veri) for veri in veriler if veri]

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        # Original title to extract year safely
        raw_title = secici.select_text("h1") or secici.select_text("div.film h1")
        title     = raw_title
        if title and title.endswith(")") and "(" in title:
            title = title.split("(")[0].strip()

        poster      = secici.select_poster("div.fposter img") or secici.select_poster("div.poster img") or secici.select_poster("img")
        description = secici.select_text("div.fdesc") or secici.select_text(".full-text") or secici.select_text("div.description p") or secici.select_text("div.description")

        # Tags from short-info under "Tür"
        tags = []
        for item in secici.select("div.short-info"):
            text = item.text(strip=True)
            if text.startswith("Tür:"):
                tags = [a.text(strip=True).replace(" Filmleri", "").replace(" Filmi", "") for a in item.select("a")]
                break

        # If no tags, fallback to breadcrumbs
        if not tags:
            tags = secici.select_texts("ol.scheme-breadcrumbs li a")
            tags = [tag.replace("✅ ", "").replace(" Filmleri", "") for tag in tags if tag != "Film izle"]

        # Metadata extraction
        rating = None

        # Year from title or metadata
        year = None
        if raw_title:
            year = secici.regex_first(r"\((\d{4})\)", raw_title)

        # Actors from short-info under "Oyuncular"
        actors = []
        for item in secici.select("div.short-info"):
            text = item.text(strip=True)
            if text.startswith("Oyuncular:"):
                actors = [a.text(strip=True) for a in item.select("a")]
                break

        # Duration from foriginal under "Süre"
        duration      = None
        duration_text = secici.select_text(".foriginal")
        if duration_text and "süre" in duration_text.lower():
            duration_match = re.search(r"(\d+)", duration_text)
            if duration_match:
                duration = int(duration_match.group(1))

        if not duration:
            duration_match = re.search(r"(\d+)\s*dakika", istek.text, re.I)
            if duration_match:
                duration = int(duration_match.group(1))

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            year        = str(year) if year else None,
            rating      = str(rating) if rating else None,
            tags        = tags,
            actors      = actors,
            duration    = duration,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        iframes = []
        for iframe in secici.select("div.fplayer iframe"):
            src = iframe.attrs.get("src")
            if src:
                iframes.append(self.fix_url(src))

        # Fallback to regex
        if not iframes:
            matches = secici.regex_all(r'<iframe[^>]+src=["\'](?!about:blank)([^"\']+)')
            for m in matches:
                iframes.append(self.fix_url(m))

        results = []
        for iframe in iframes:
            if "youtube.com" in iframe or "youtube-nocookie.com" in iframe or iframe == "about:blank" or iframe.startswith("javascript:"):
                continue

            result = await self.extract(iframe)
            if result:
                results.append(result)

        return results
