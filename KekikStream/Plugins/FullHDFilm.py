# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, Subtitle
from parsel import Selector
import re, base64

class FullHDFilm(PluginBase):
    name        = "FullHDFilm"
    language    = "tr"
    main_url    = "https://hdfilm.us"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Full HD Film izle, Türkçe Dublaj ve Altyazılı filmler."

    main_page   = {
        f"{main_url}/tur/turkce-altyazili-film-izle"     : "Altyazılı Filmler",
        f"{main_url}/tur/netflix-filmleri-izle"          : "Netflix",
        f"{main_url}/category/aile-filmleri-izle"        : "Aile",
        f"{main_url}/category/aksiyon-filmleri-izle"     : "Aksiyon",
        f"{main_url}/category/animasyon-filmleri-izle"   : "Animasyon",
        f"{main_url}/category/belgesel-filmleri-izle"    : "Belgesel",
        f"{main_url}/category/bilim-kurgu-filmleri-izle" : "Bilim-Kurgu",
        f"{main_url}/category/biyografi-filmleri-izle"   : "Biyografi",
        f"{main_url}/category/dram-filmleri-izle"        : "Dram",
        f"{main_url}/category/fantastik-filmler-izle"    : "Fantastik",
        f"{main_url}/category/gerilim-filmleri-izle"     : "Gerilim",
        f"{main_url}/category/gizem-filmleri-izle"       : "Gizem",
        f"{main_url}/category/komedi-filmleri-izle"      : "Komedi",
        f"{main_url}/category/korku-filmleri-izle"       : "Korku",
        f"{main_url}/category/macera-filmleri-izle"      : "Macera",
        f"{main_url}/category/romantik-filmler-izle"     : "Romantik",
        f"{main_url}/category/savas-filmleri-izle"       : "Savaş",
        f"{main_url}/category/suc-filmleri-izle"         : "Suç",
        f"{main_url}/tur/yerli-film-izle"                : "Yerli Film",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        page_url = url if page == 1 else f"{url}/page/{page}"

        self.httpx.headers.update({
            "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer"    : f"{self.main_url}/"
        })

        istek  = await self.httpx.get(page_url)
        secici = Selector(istek.text)

        return [
            MainPageResult(
                category = category,
                title    = veri.css("img::attr(alt)").get(),
                url      = self.fix_url(veri.css("a::attr(href)").get()),
                poster   = self.fix_url(veri.css("img::attr(src)").get()),
            )
                for veri in secici.css("div.movie-poster")
                    if veri.css("img::attr(alt)").get()
        ]

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = Selector(istek.text)

        return [
            SearchResult(
                title  = veri.css("img::attr(alt)").get(),
                url    = self.fix_url(veri.css("a::attr(href)").get()),
                poster = self.fix_url(veri.css("img::attr(src)").get()),
            )
                for veri in secici.css("div.movie-poster")
                    if veri.css("img::attr(alt)").get()
        ]

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        title       = secici.css("h1::text").get() or ""
        title       = title.strip() if title else ""
        poster      = self.fix_url(secici.css("div.poster img::attr(src)").get() or "")
        
        actors_text = secici.css("div.oyuncular.info::text").get()
        if actors_text:
            actors_text = actors_text.replace("Oyuncular:", "").strip()
            actors = [a.strip() for a in actors_text.split(",")]
        else:
            actors = []

        year   = secici.css("div.yayin-tarihi.info::text").re_first(r"(\d{4})")
        tags   = secici.css("div.tur.info a::text").getall()
        rating = secici.css("div.imdb::text").re_first(r"IMDb\s*([\d\.]+)")
        
        # Description
        description = secici.xpath("//div[contains(@class, 'others')]/preceding-sibling::div[1]//text()").getall()
        description = "".join(description).strip() if description else None

        # Kotlin referansı: URL'de -dizi kontrolü veya tags içinde "dizi" kontrolü
        is_series = "-dizi" in url.lower() or any("dizi" in tag.lower() for tag in tags)

        if is_series:
            episodes = []
            part_elements = secici.css("li.psec")
            part_names    = secici.css("li.psec a::text").getall()
            
            # pdata değerlerini çıkar
            pdata_matches = re.findall(r"pdata\['([^']+)'\]\s*=\s*'([^']+)'", istek.text)
            
            for idx, (part_id, part_name) in enumerate(zip([el.css("::attr(id)").get() for el in part_elements], part_names)):
                if not part_name:
                    continue
                    
                part_name = part_name.strip()
                
                # Fragman'ları atla
                if "fragman" in part_name.lower() or (part_id and "fragman" in part_id.lower()):
                    continue
                
                # Sezon ve bölüm numarası çıkar
                sz_match = re.search(r'(\d+)\s*sezon', part_id.lower() if part_id else "")
                ep_match = re.search(r'^(\d+)\.', part_name)
                
                sz_num = int(sz_match.group(1)) if sz_match else 1
                ep_num = int(ep_match.group(1)) if ep_match else idx + 1
                
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
                rating      = rating.strip() if rating else None,
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
                rating      = rating.strip() if rating else None,
            )

    def _get_iframe(self, source_code: str) -> str:
        """Base64 kodlu iframe'i çözümle"""
        match = re.search(r'<script[^>]*>(PCEtLWJhc2xpazp[^<]*)</script>', source_code)
        if not match:
            return ""

        try:
            decoded_html = base64.b64decode(match[1]).decode("utf-8")
            iframe_match = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', decoded_html)
            return self.fix_url(iframe_match[1]) if iframe_match else ""
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
            if match := re.search(pattern, source_code):
                return match[1]

        return None

    async def load_links(self, url: str) -> list[dict]:
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
                data["subtitles"] = [Subtitle(name="Türkçe", url=subtitle_url)] if subtitle_url else []
                results.append(data)

        return results
