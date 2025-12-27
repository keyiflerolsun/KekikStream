# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, Subtitle, ExtractResult
from selectolax.parser import HTMLParser
from Kekik.Sifreleme   import Packer, StreamDecoder
import random, string, re

class HDFilmCehennemi(PluginBase):
    name        = "HDFilmCehennemi"
    language    = "tr"
    main_url    = "https://www.hdfilmcehennemi.ws"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Türkiye'nin en hızlı hd film izleme sitesi. Tek ve gerçek hdfilmcehennemi sitesi."

    main_page   = {
        f"{main_url}"                                      : "Yeni Eklenen Filmler",
        f"{main_url}/yabancidiziizle-2"                    : "Yeni Eklenen Diziler",
        f"{main_url}/category/tavsiye-filmler-izle2"       : "Tavsiye Filmler",
        f"{main_url}/imdb-7-puan-uzeri-filmler"            : "IMDB 7+ Filmler",
        f"{main_url}/en-cok-yorumlananlar-1"               : "En Çok Yorumlananlar",
        f"{main_url}/en-cok-begenilen-filmleri-izle"       : "En Çok Beğenilenler",
        f"{main_url}/tur/aile-filmleri-izleyin-6"          : "Aile Filmleri",
        f"{main_url}/tur/aksiyon-filmleri-izleyin-3"       : "Aksiyon Filmleri",
        f"{main_url}/tur/animasyon-filmlerini-izleyin-4"   : "Animasyon Filmleri",
        f"{main_url}/tur/belgesel-filmlerini-izle-1"       : "Belgesel Filmleri",
        f"{main_url}/tur/bilim-kurgu-filmlerini-izleyin-2" : "Bilim Kurgu Filmleri",
        f"{main_url}/tur/komedi-filmlerini-izleyin-1"      : "Komedi Filmleri",
        f"{main_url}/tur/korku-filmlerini-izle-2/"         : "Korku Filmleri",
        f"{main_url}/tur/romantik-filmleri-izle-1"         : "Romantik Filmleri"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}", follow_redirects=True)
        secici = HTMLParser(istek.text)

        results = []
        for veri in secici.css("div.section-content a.poster"):
            title_el = veri.css_first("strong.poster-title")
            img_el   = veri.css_first("img")

            title  = title_el.text(strip=True) if title_el else None
            href   = veri.attrs.get("href")
            poster = img_el.attrs.get("data-src") if img_el else None

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster) if poster else None,
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek = await self.httpx.get(
            url     = f"{self.main_url}/search/?q={query}",
            headers = {
                "Referer"          : f"{self.main_url}/",
                "X-Requested-With" : "fetch",
                "authority"        : f"{self.main_url}"
            }
        )

        results = []
        for veri in istek.json().get("results", []):
            secici = HTMLParser(veri)
            title_el = secici.css_first("h4.title")
            link_el  = secici.css_first("a")
            img_el   = secici.css_first("img")

            title  = title_el.text(strip=True) if title_el else None
            href   = link_el.attrs.get("href") if link_el else None
            poster = (img_el.attrs.get("data-src") or img_el.attrs.get("src")) if img_el else None
            
            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster) if poster else None,
                ))
            
        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url, headers = {"Referer": f"{self.main_url}/"})
        secici = HTMLParser(istek.text)

        title_el = secici.css_first("h1.section-title")
        title    = title_el.text(strip=True) if title_el else ""

        poster_el = secici.css_first("aside.post-info-poster img.lazyload")
        poster    = poster_el.attrs.get("data-src", "").strip() if poster_el else ""

        desc_el     = secici.css_first("article.post-info-content > p")
        description = desc_el.text(strip=True) if desc_el else ""

        tags   = [a.text(strip=True) for a in secici.css("div.post-info-genres a") if a.text(strip=True)]

        rating_el = secici.css_first("div.post-info-imdb-rating span")
        rating    = rating_el.text(strip=True) if rating_el else ""

        year_el = secici.css_first("div.post-info-year-country a")
        year    = year_el.text(strip=True) if year_el else ""

        actors = [a.text(strip=True) for a in secici.css("div.post-info-cast a > strong") if a.text(strip=True)]

        duration_el = secici.css_first("div.post-info-duration")
        duration_str = duration_el.text(strip=True) if duration_el else "0"
        duration_str = duration_str.replace("dakika", "").strip()

        try:
            duration_match = re.search(r'\d+', duration_str)
            duration_minutes = int(duration_match.group()) if duration_match else 0
        except Exception:
            duration_minutes = 0

        # Dizi mi film mi kontrol et (Kotlin referansı: div.seasons kontrolü)
        is_series = len(secici.css("div.seasons")) > 0

        if is_series:
            episodes = []
            for ep in secici.css("div.seasons-tab-content a"):
                ep_name_el = ep.css_first("h4")
                ep_name = ep_name_el.text(strip=True) if ep_name_el else None
                ep_href = ep.attrs.get("href")

                if ep_name and ep_href:
                    # Regex ile sezon ve bölüm numarası çıkar
                    ep_match = re.search(r'(\d+)\.\s*Bölüm', ep_name)
                    sz_match = re.search(r'(\d+)\.\s*Sezon', ep_name)
                    ep_num = int(ep_match.group(1)) if ep_match else 1
                    sz_num = int(sz_match.group(1)) if sz_match else 1
                    
                    episodes.append(Episode(
                        season  = sz_num,
                        episode = ep_num,
                        title   = ep_name,
                        url     = self.fix_url(ep_href)
                    ))

            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster) if poster else None,
                title       = self.clean_title(title),
                description = description,
                tags        = tags,
                rating      = rating,
                year        = year,
                actors      = actors,
                episodes    = episodes
            )
        else:
            return MovieInfo(
                url         = url,
                poster      = self.fix_url(poster) if poster else None,
                title       = self.clean_title(title),
                description = description,
                tags        = tags,
                rating      = rating,
                year        = year,
                actors      = actors,
                duration    = duration_minutes
            )

    def generate_random_cookie(self):
        return "".join(random.choices(string.ascii_letters + string.digits, k=16))

    async def cehennempass(self, video_id: str) -> list:
        results = []
        
        istek = await self.httpx.post(
            url     = "https://cehennempass.pw/process_quality_selection.php",
            headers = {
                "Referer"          : f"https://cehennempass.pw/download/{video_id}", 
                "X-Requested-With" : "fetch", 
                "authority"        : "cehennempass.pw",
                "Cookie"           : f"PHPSESSID={self.generate_random_cookie()}"
            },
            data    = {"video_id": video_id, "selected_quality": "low"},
        )
        if video_url := istek.json().get("download_link"):
            results.append(ExtractResult(
                url     = self.fix_url(video_url),
                name    = "Düşük Kalite",
                referer = f"https://cehennempass.pw/download/{video_id}"
            ))

        istek = await self.httpx.post(
            url     = "https://cehennempass.pw/process_quality_selection.php",
            headers = {
                "Referer"          : f"https://cehennempass.pw/download/{video_id}", 
                "X-Requested-With" : "fetch", 
                "authority"        : "cehennempass.pw",
                "Cookie"           : f"PHPSESSID={self.generate_random_cookie()}"
            },
            data    = {"video_id": video_id, "selected_quality": "high"},
        )
        if video_url := istek.json().get("download_link"):
            results.append(ExtractResult(
                url     = self.fix_url(video_url),
                name    = "Yüksek Kalite",
                referer = f"https://cehennempass.pw/download/{video_id}"
            ))

        return results

    def extract_hdch_url(self, unpacked: str) -> str:
        """HDFilmCehennemi unpacked script'ten video URL'sini çıkar"""
        # 1) Decode fonksiyonunun adını bul: function <NAME>(value_parts)
        match_fn = re.search(r'function\s+(\w+)\s*\(\s*value_parts\s*\)', unpacked)
        if not match_fn:
            return ""
        
        fn_name = match_fn.group(1)
        
        # 2) Bu fonksiyonun array ile çağrıldığı yeri bul: <NAME>([ ... ])
        array_call_regex = re.compile(rf'{re.escape(fn_name)}\(\s*\[(.*?)\]\s*\)', re.DOTALL)
        match_call = array_call_regex.search(unpacked)
        if not match_call:
            return ""

        array_body = match_call.group(1)

        # 3) Array içindeki string parçalarını topla
        parts = re.findall(r'["\']([^"\']+)["\']', array_body)
        if not parts:
            return ""

        # 4) Özel decoder ile çöz
        return StreamDecoder._brute_force(parts)

    async def invoke_local_source(self, iframe: str, source: str, url: str):
        self.httpx.headers.update({
            "Referer": f"{self.main_url}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0"
        })
        istek = await self.httpx.get(iframe)

        if not istek.text:
            return await self.cehennempass(iframe.split("/")[-1])

        # eval(function...) içeren packed script bul
        eval_match = re.search(r'(eval\(function[\s\S]+)', istek.text)
        if not eval_match:
            return await self.cehennempass(iframe.split("/")[-1])

        try:
            unpacked = Packer.unpack(eval_match.group(1))
        except Exception:
            return await self.cehennempass(iframe.split("/")[-1])

        # HDFilmCehennemi özel decoder ile video URL'sini çıkar
        video_url = self.extract_hdch_url(unpacked)
        
        if not video_url:
            return await self.cehennempass(iframe.split("/")[-1])

        subtitles = []
        try:
            sub_data = istek.text.split("tracks: [")[1].split("]")[0]
            for sub in re.findall(r'file":"([^"]+)".*?"language":"([^"]+)"', sub_data, flags=re.DOTALL):
                subtitles.append(Subtitle(
                    name = sub[1].upper(),
                    url  = self.fix_url(sub[0].replace("\\", "")),
                ))
        except Exception:
            pass

        return [ExtractResult(
            url       = video_url,
            name      = source,
            referer   = url,
            subtitles = subtitles
        )]

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)

        results = []
        for alternatif in secici.css("div.alternative-links"):
            lang_code = alternatif.attrs.get("data-lang", "").upper()

            for link in alternatif.css("button.alternative-link"):
                source_text = link.text(strip=True).replace('(HDrip Xbet)', '').strip()
                source   = f"{source_text} {lang_code}"
                video_id = link.attrs.get("data-video")

                if not video_id:
                    continue

                api_get = await self.httpx.get(
                    url     = f"{self.main_url}/video/{video_id}/",
                    headers = {
                        "Content-Type"     : "application/json",
                        "X-Requested-With" : "fetch",
                        "Referer"          : url,
                    },
                )

                match  = re.search(r'data-src=\\\"([^"]+)', api_get.text)
                iframe = match[1].replace("\\", "") if match else None

                if not iframe:
                    continue

                # mobi URL'si varsa direkt kullan (query string'i kaldır)
                if "mobi" in iframe:
                    iframe = iframe.split("?")[0]  # rapidrame_id query param'ı kaldır
                # mobi değilse ve rapidrame varsa rplayer kullan
                elif "rapidrame" in iframe and "?rapidrame_id=" in iframe:
                    iframe = f"{self.main_url}/rplayer/{iframe.split('?rapidrame_id=')[1]}"

                video_data_list = await self.invoke_local_source(iframe, source, url)
                if not video_data_list:
                    continue

                for video_data in video_data_list:
                    results.append(video_data)

        return results