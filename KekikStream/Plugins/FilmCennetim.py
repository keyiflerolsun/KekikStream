# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper
import re

class FilmCennetim(PluginBase):
    name        = "FilmCennetim"
    language    = "tr"
    main_url    = "https://filmcennetim.com"
    favicon     = "https://filmcennetim.com/wp-content/uploads/2026/02/film-cenneti-logo.png"
    description = "Film Cenneti, Türkçe dublaj ve 1080p kalitede en yeni filmleri HD izleyebileceğiniz bir platformdur. Hızlı, reklamsız ve kesintisiz sinema keyfi!."

    main_page   = {
        f"{main_url}/Kategori/tur/aile-filmleri"        : "Aile",
        f"{main_url}/Kategori/tur/aksiyon-filmleri"     : "Aksiyon",
        f"{main_url}/Kategori/tur/animasyon-filmleri"   : "Animasyon",
        f"{main_url}/Kategori/tur/anime-filmleri"       : "Anime",
        f"{main_url}/Kategori/tur/belgeseler-filmleri"  : "Belgeseler",
        f"{main_url}/Kategori/tur/bilim-kurgu-filmleri" : "Bilim-Kurgu",
        f"{main_url}/Kategori/tur/biyografi-filmleri"   : "Biyoğrafi",
        f"{main_url}/Kategori/dizi-izle"                : "Diziler",
        f"{main_url}/Kategori/tur/dram-filmleri-hd"     : "Dram",
        f"{main_url}/Kategori/tur/erotik-filmleri"      : "Erotik",
        f"{main_url}/Kategori/tur/fantastik-filmler"    : "Fantastik",
        f"{main_url}/Kategori/tur/gerilim-filmleri-hd"  : "Gerilim",
        f"{main_url}/Kategori/tur/gizem-filmleri"       : "Gizem",
        f"{main_url}/Kategori/tur/hint-filmleri"        : "Hint",
        f"{main_url}/Kategori/tur/komedi-filmleri"      : "Komedi",
        f"{main_url}/Kategori/tur/korku-filmleri"       : "Korku",
        f"{main_url}/Kategori/tur/macera-filmleri"      : "Macera",
        f"{main_url}/Kategori/tur/muzikal-filmleri"     : "Müzikal",
        f"{main_url}/Kategori/tur/netflix-filmleri"     : "Netflix",
        f"{main_url}/Kategori/tur/romantik-filmleri"    : "Romantik",
        f"{main_url}/Kategori/tur/savas-filmleri"       : "Savaş",
        f"{main_url}/Kategori/tur/spor-filmleri"        : "Spor",
        f"{main_url}/Kategori/tur/suc-filmleri"         : "Suç",
        f"{main_url}/Kategori/tur/tarihi-filmleri"      : "Tarihi",
        f"{main_url}/Kategori/tur/western-filmleri"     : "Western",
        f"{main_url}/Kategori/tur/yerli-filmleri"       : "Yerli",
    }

    async def get_articles(self, secici: HTMLHelper) -> list[dict]:
        articles = []
        for veri in secici.select("article.movie-box"):
            title  = veri.select_text("div.name a") or veri.select_attr("div.name a", "title") or veri.select_attr("a", "title")
            href   = veri.select_attr("div.name a", "href") or veri.select_attr("a", "href")
            poster = veri.select_poster("img")

            if title and href:
                articles.append({
                    "title"  : title,
                    "url"    : self.fix_url(href),
                    "poster" : self.fix_url(poster),
                })

        return articles

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek   = await self.httpx.get(f"{url}/{page}")
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
        raw_title   = secici.select_text("div.film h1")
        title       = raw_title
        poster      = secici.select_poster("div.poster img")
        description = secici.select_text("div.description p") or secici.select_text("div.description")

        # Tags from breadcrumbs or tags div
        tags = secici.select_texts("ol.scheme-breadcrumbs li a")
        tags = [tag.replace("✅ ", "").replace(" Filmleri", "") for tag in tags if tag != "Film izle"]

        # Metadata extraction
        rating = secici.meta_value("IMDb")
        # 1080p gibi değerleri yıl sanmaması için regex'i daraltalım
        year     = secici.extract_year("div.metadata span a[href*='/yapim/']")
        actors   = secici.meta_list("Oyuncular")
        duration = None

        if not duration:
            duration_match = re.search(r"(\d+)\s*dakika", istek.text, re.I)
            if duration_match:
                duration = int(duration_match.group(1))

        # Fallback: Eğer meta_value/list bulamadıysa sınıf listesine bak
        meta_node = secici.select_first(".post")
        classes   = meta_node.attrs.get("class", "").split() if meta_node else []

        for cls in classes:
            if cls.startswith("oyuncular-"):
                actor_name = cls.replace("oyuncular-", "").replace("-", " ").title()
                if actor_name not in actors:
                    actors.append(actor_name)
            elif not rating and cls.startswith("imdb-"):
                rating = cls.replace("imdb-", "").replace("-", ".")
            elif not year and cls.startswith("yapim-"):
                y_val = cls.replace("yapim-", "").replace("yili-", "")
                if y_val.isdigit() and 1900 < int(y_val) < 2100:
                    year = y_val

        # Hala yıl yoksa başlıktan çıkar (Orijinal başlıktan!)
        if not year:
            year = secici.regex_first(r"\((\d{4})\)", raw_title)

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

        iframe = secici.select_attr("div.video-content iframe", "src")
        if iframe == "about:blank":
            iframe = None

        if not iframe:
            iframe = secici.regex_first(r'<iframe[^>]+src=["\'](?!about:blank)([^"\']+)')

        if not iframe:
            return []

        iframe = self.fix_url(iframe)
        if iframe == "about:blank" or iframe.startswith("javascript:"):
            return []

        result = await self.extract(iframe)

        return [result] if result else []
