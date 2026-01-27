# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, Subtitle, HTMLHelper
import base64

class FullHDFilm(PluginBase):
    name        = "FullHDFilm"
    language    = "tr"
    main_url    = "https://hdfilm.us"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Full HD Film izle, Türkçe Dublaj ve Altyazılı filmler."

    main_page   = {
        f"{main_url}/tur/turkce-altyazili-film-izle"     : "Altyazılı Filmler",
        f"{main_url}/tur/netflix-filmleri-izle"          : "Netflix",
        f"{main_url}/tur/yerli-film-izle"                : "Yerli Film",
        f"{main_url}/category/aile-filmleri-izle"        : "Aile",
        f"{main_url}/category/aksiyon-filmleri-izle"     : "Aksiyon",
        f"{main_url}/category/animasyon-filmleri-izle"   : "Animasyon",
        f"{main_url}/category/belgesel-filmleri-izle"    : "Belgesel",
        f"{main_url}/category/bilim-kurgu-filmleri-izle" : "Bilim Kurgu",
        f"{main_url}/category/biyografi-filmleri-izle"   : "Biyografi",
        f"{main_url}/category/dram-filmleri-izle"        : "Dram",
        f"{main_url}/category/fantastik-filmler-izle"    : "Fantastik",
        f"{main_url}/category/gerilim-filmleri-izle"     : "Gerilim",
        f"{main_url}/category/gizem-filmleri-izle"       : "Gizem",
        f"{main_url}/category/kisa"                      : "Kısa",
        f"{main_url}/category/komedi-filmleri-izle"      : "Komedi",
        f"{main_url}/category/korku-filmleri-izle"       : "Korku",
        f"{main_url}/category/macera-filmleri-izle"      : "Macera",
        f"{main_url}/category/muzik"                     : "Müzik",
        f"{main_url}/category/muzikal-filmleri-izle"     : "Müzikal",
        f"{main_url}/category/romantik-filmler-izle"     : "Romantik",
        f"{main_url}/category/savas-filmleri-izle"       : "Savaş",
        f"{main_url}/category/spor-filmleri-izle"        : "Spor",
        f"{main_url}/category/suc-filmleri-izle"         : "Suç",
        f"{main_url}/category/tarih-filmleri-izle"       : "Tarih",
        f"{main_url}/category/western-filmleri-izle"     : "Western",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        page_url = url if page == 1 else f"{url}/page/{page}"

        self.httpx.headers.update({
            "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer"    : f"{self.main_url}/"
        })

        istek  = await self.httpx.get(page_url)
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movie-poster"):
            alt = secici.select_attr("img", "alt", veri)
            poster = secici.select_attr("img", "src", veri)
            href = secici.select_attr("a", "href", veri)

            if alt and href:
                results.append(MainPageResult(
                    category = category,
                    title    = alt,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movie-poster"):
            alt = secici.select_attr("img", "alt", veri)
            poster = secici.select_attr("img", "src", veri)
            href = secici.select_attr("a", "href", veri)

            if alt and href:
                results.append(SearchResult(
                    title  = alt,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = self.clean_title(secici.select_text("h1"))
        poster      = secici.select_poster("div.poster img")
        description = secici.select_text("div.film") or secici.select_attr("meta[property='og:description']", "content")
        year        = secici.extract_year("div.yayin-tarihi.info") or secici.regex_first(r"\((\d{4})\)")
        tags        = secici.select_texts("div.tur.info a")
        rating      = secici.regex_first(r"IMDb\s*([\d\.]+)", secici.select_text("div.imdb"))
        actors      = secici.select_direct_text("div.oyuncular")

        # Kotlin referansı: URL'de -dizi veya tags içinde dizi kontrolü
        is_series = "-dizi" in url.lower() or any("dizi" in tag.lower() for tag in tags)

        if is_series:
            episodes = []
            for idx, el in enumerate(secici.select("li.psec")):
                part_id   = el.attrs.get("id")
                part_name = secici.select_text("a", el) or ""
                if not part_name or "fragman" in part_name.lower(): continue
                
                s, e = secici.extract_season_episode(f"{part_id} {part_name}")
                episodes.append(Episode(season=s or 1, episode=e or (idx+1), title=f"{s or 1}. Sezon {e or idx+1}. Bölüm", url=url))

            return SeriesInfo(
                url=url, poster=self.fix_url(poster), title=title, description=description,
                tags=tags, year=year, actors=actors, rating=rating, episodes=episodes
            )

        return MovieInfo(
            url=url, poster=self.fix_url(poster), title=title, description=description,
            tags=tags, year=year, actors=actors, rating=rating
        )

    def _get_iframe(self, source_code: str) -> str:
        """Base64 kodlu iframe'i çözümle"""
        script_val = HTMLHelper(source_code).regex_first(r'<script[^>]*>(PCEtLWJhc2xpazp[^<]*)</script>')
        if not script_val:
            return ""

        try:
            decoded_html = base64.b64decode(script_val).decode("utf-8")
            iframe_src = HTMLHelper(decoded_html).regex_first(r'<iframe[^>]+src=["\']([^"\']+)["\']')
            return self.fix_url(iframe_src) if iframe_src else ""
        except Exception:
            return ""

    def _extract_subtitle_url(self, source_code: str) -> str | None:
        """playerjsSubtitle değişkeninden .srt URL çıkar"""
        patterns = [
            r'var playerjsSubtitle = "\[Türkçe\](https?://[^\s"]+?\.srt)";',
            r'var playerjsSubtitle = "(https?://[^\s"]+?\.srt)";',
            r'subtitle:\s*"(https?://[^\s"]+?\.srt)"',
        ]

        for pattern in patterns:
            val = HTMLHelper(source_code).regex_first(pattern)
            if val:
                return val

        return None

    async def load_links(self, url: str) -> list[ExtractResult]:
        self.httpx.headers.update({
            "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer"    : self.main_url
        })

        istek       = await self.httpx.get(url)
        source_code = istek.text

        # Ana sayfadan altyazı URL'sini çek
        subtitle_url = self._extract_subtitle_url(source_code)

        # Iframe'den altyazı URL'sini çek
        iframe_src = self._get_iframe(source_code)

        if not subtitle_url and iframe_src:
            iframe_istek = await self.httpx.get(iframe_src)
            subtitle_url = self._extract_subtitle_url(iframe_istek.text)

        results = []

        if iframe_src:
            data = await self.extract(iframe_src)
            if data:
                # ExtractResult objesi immutable, yeni bir kopya oluştur
                subtitles = [Subtitle(name="Türkçe", url=subtitle_url)] if subtitle_url else []
                updated_data = data.model_copy(update={"subtitles": subtitles}) if subtitles else data
                results.append(updated_data)

        return results
