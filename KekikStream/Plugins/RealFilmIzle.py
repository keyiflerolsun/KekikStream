# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper

class RealFilmIzle(PluginBase):
    name        = "RealFilmIzle"
    language    = "tr"
    main_url    = "https://filmizlefullhd.live"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "realfilmizle.com, sinemayı seven kullanıcılar için hazırlanmış, zengin içerik yapısına sahip bir online film izleme sitesidir."

    main_page   = {
        f"{main_url}/dizi/aile-filmleri/page"        : "Aile",
        f"{main_url}/dizi/aksiyon-filmleri/page"     : "Aksiyon",
        f"{main_url}/dizi/animasyon-filmleri/page"   : "Animasyon",
        f"{main_url}/dizi/anime-filmleri/page"       : "Anime",
        f"{main_url}/dizi/belgeseler-filmleri/page"  : "Belgeseler",
        f"{main_url}/dizi/bilim-kurgu-filmleri/page" : "Bilim-Kurgu",
        f"{main_url}/dizi/biyografi-filmleri/page"   : "Biyoğrafi",
        f"{main_url}/dizi/dram-filmleri/page"        : "Dram",
        f"{main_url}/dizi/erotik-filmleri/page"      : "Erotik",
        f"{main_url}/dizi/fantastik-filmleri/page"   : "Fantastik",
        f"{main_url}/dizi/gerilim-filmleri/page"     : "Gerilim",
        f"{main_url}/dizi/gizem-filmleri/page"       : "Gizem",
        f"{main_url}/dizi/hint-filmleri/page"        : "Hint",
        f"{main_url}/dizi/komedi-filmleri/page"      : "Komedi",
        f"{main_url}/dizi/korku-filmleri/page"       : "Korku",
        f"{main_url}/dizi/macera-filmleri/page"      : "Macera",
        f"{main_url}/dizi/muzikal-filmleri/page"     : "Müzikal",
        f"{main_url}/dizi/netflix-filmleri/page"     : "Netflix",
        f"{main_url}/dizi/romantik-filmleri/page"    : "Romantik",
        f"{main_url}/dizi/savas-filmleri/page"       : "Savaş",
        f"{main_url}/dizi/spor-filmleri/page"        : "Spor",
        f"{main_url}/dizi/suc-filmleri/page"         : "Suç",
        f"{main_url}/dizi/tarihi-filmleri/page"      : "Tarihi",
        f"{main_url}/dizi/western-filmleri/page"     : "Western",
        f"{main_url}/dizi/yerli-filmleri/page"       : "Yerli",
    }

    async def get_articles(self, secici: HTMLHelper) -> list[dict]:
        articles = []
        for veri in secici.select("article.movie-box"):
            title  = secici.select_text("div.name a", veri) or secici.select_attr("div.name a", "title", veri) or secici.select_attr("a", "title", veri)
            href   = secici.select_attr("div.name a", "href", veri) or secici.select_attr("a", "href", veri)
            poster = secici.select_poster("img", veri)

            if title and href:
                articles.append({
                    "title" : self.clean_title(title),
                    "url"   : self.fix_url(href),
                    "poster": self.fix_url(poster),
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
        title       = self.clean_title(raw_title)
        poster      = secici.select_poster("div.poster img")
        description = secici.select_text("div.description p") or secici.select_text("div.description")

        # Tags from breadcrumbs or tags div
        tags        = secici.select_texts("ol.scheme-breadcrumbs li a")
        tags        = [tag.replace("✅ ", "").replace(" Filmleri", "") for tag in tags if tag != "Film izle"]

        # Metadata extraction
        rating = secici.meta_value("IMDb")
        # 1080p gibi değerleri yıl sanmaması için regex'i daraltalım
        year   = secici.extract_year("div.metadata span a[href*='/yapim/']")
        actors = secici.meta_list("Oyuncular")

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
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        iframe = secici.select_attr("div.video-content iframe", "src")
        result = await self.extract(iframe)

        return [result] if result else []
