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
                    poster   = self.fix_url(poster) if poster else None,
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
                    poster = self.fix_url(poster) if poster else None,
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)
        html_text = istek.text

        title = secici.select_text("h1") or ""

        poster = secici.select_attr("div.poster img", "src") or ""
        poster = self.fix_url(poster)
        
        actors = []
        actors_text = secici.select_text("div.oyuncular.info")
        if actors_text:
            actors_text = actors_text.replace("Oyuncular:", "").strip()
            actors = [a.strip() for a in actors_text.split(",")]

        # Year: önce div.yayin-tarihi.info dene
        year = secici.extract_year("div.yayin-tarihi.info")

        # Fallback: h1'in parent'ından (2019) formatında ara
        if not year:
            # Parent'ın tüm text içeriğinden yıl çıkar
            title_text = secici.select_text("h1")
            if title_text:
                # h1 parent'ındaki (2019) gibi text'i bul
                year = secici.regex_first(r"\((\d{4})\)")

        tags = secici.select_all_text("div.tur.info a")

        # Rating: regex
        rating_text = secici.select_text("div.imdb") or ""
        rating = HTMLHelper(rating_text).regex_first(r"IMDb\s*([\d\.]+)")
        
        # Description: önce div.film dene, yoksa og:description meta tag'ını kullan
        description = secici.select_text("div.film")
        
        # Fallback: og:description meta tag'ı
        if not description:
            og_desc = secici.select_attr("meta[property='og:description']", "content")
            if og_desc:
                description = og_desc

        # Kotlin referansı: URL'de -dizi kontrolü veya tags içinde "dizi" kontrolü
        is_series = "-dizi" in url.lower() or any("dizi" in tag.lower() for tag in tags)

        if is_series:
            episodes = []
            part_elements = secici.select("li.psec")
            
            # pdata değerlerini çıkar
            pdata_matches = HTMLHelper(html_text).regex_all(r"pdata\['([^']+)'\]\s*=\s*'([^']+)'")
            
            for idx, el in enumerate(part_elements):
                part_id = el.attrs.get("id")
                part_name = secici.select_text("a", el)

                if not part_name:
                    continue
                
                # Fragman'ları atla
                if "fragman" in part_name.lower() or (part_id and "fragman" in part_id.lower()):
                    continue
                
                # Sezon ve bölüm numarası çıkar
                sz_val = HTMLHelper(part_id.lower() if part_id else "").regex_first(r'(\d+)\s*sezon')
                ep_val = HTMLHelper(part_name).regex_first(r'^(\d+)\.')

                sz_num = int(sz_val) if sz_val and sz_val.isdigit() else 1
                ep_num = int(ep_val) if ep_val and ep_val.isdigit() else idx + 1
                
                # pdata'dan video URL'si çık (varsa)
                video_url = url  # Varsayılan olarak ana URL kullan
                if idx < len(pdata_matches):
                    video_url = pdata_matches[idx][1] if pdata_matches[idx][1] else url
                
                episodes.append(Episode(
                    season  = sz_num,
                    episode = ep_num,
                    title   = f"{sz_num}. Sezon {ep_num}. Bölüm",
                    url     = url  # Bölüm URL'leri load_links'te işlenecek
                ))

            return SeriesInfo(
                url         = url,
                poster      = poster,
                title       = self.clean_title(title) if title else "",
                description = description,
                tags        = tags,
                year        = year,
                actors      = actors,
                rating      = rating,
                episodes    = episodes
            )
        else:
            return MovieInfo(
                url         = url,
                poster      = poster,
                title       = self.clean_title(title) if title else "",
                description = description,
                tags        = tags,
                year        = year,
                actors      = actors,
                rating      = rating,
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
