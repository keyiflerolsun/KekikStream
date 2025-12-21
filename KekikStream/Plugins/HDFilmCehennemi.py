# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, Subtitle
from parsel           import Selector
from Kekik.Sifreleme  import Packer, StreamDecoder
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
        secici = Selector(istek.text)

        return [
            MainPageResult(
                category = category,
                title    = veri.css("strong.poster-title::text").get(),
                url      = self.fix_url(veri.css("::attr(href)").get()),
                poster   = self.fix_url(veri.css("img::attr(data-src)").get()),
            )
                for veri in secici.css("div.section-content a.poster")
        ]

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
        for veri in istek.json().get("results"):
            secici = Selector(veri)
            title  = secici.css("h4.title::text").get()
            href   = secici.css("a::attr(href)").get()
            poster = secici.css("img::attr(data-src)").get() or secici.css("img::attr(src)").get()
            
            if title and href:
                results.append(
                    SearchResult(
                        title  = title.strip(),
                        url    = self.fix_url(href.strip()),
                        poster = self.fix_url(poster.strip()) if poster else None,
                    )
                )
            
        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url, headers = {"Referer": f"{self.main_url}/"})
        secici = Selector(istek.text)

        title       = secici.css("h1.section-title::text").get().strip()
        poster      = secici.css("aside.post-info-poster img.lazyload::attr(data-src)").get().strip()
        description = secici.css("article.post-info-content > p::text").get().strip()
        tags        = secici.css("div.post-info-genres a::text").getall()
        rating      = secici.css("div.post-info-imdb-rating span::text").get().strip()
        year        = secici.css("div.post-info-year-country a::text").get().strip()
        actors      = secici.css("div.post-info-cast a > strong::text").getall()
        duration    = secici.css("div.post-info-duration::text").get().replace("dakika", "").strip()

        
        try:
            duration_minutes = int(duration[2:-1])
        except Exception:
            duration_minutes = 0

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
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

    async def cehennempass(self, video_id: str) -> list[dict]:
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
            results.append({
                "url"     : self.fix_url(video_url),
                "name"    : "Düşük Kalite",
                "referer" : f"https://cehennempass.pw/download/{video_id}"
            })

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
            results.append({
                "url"     : self.fix_url(video_url),
                "name"    : "Yüksek Kalite",
                "referer" : f"https://cehennempass.pw/download/{video_id}"
            })

        return results

    def hdch_decode(self, value_parts: list[str]) -> str:
        """
        HDFilmCehennemi için özel decoder.
        JavaScript sırası: join -> reverse -> atob -> atob -> shift_back
        """
        try:
            # 1. Parçaları birleştir
            joined = ''.join(value_parts)
            
            # 2. Ters çevir (REV)
            result = StreamDecoder._reverse(joined)
            
            # 3. İlk base64 decode (B64D)
            result = StreamDecoder._base64_decode(result)
            if result is None:
                return ""
            
            # 4. İkinci base64 decode (B64D) - JavaScript'te iki kez atob yapılıyor!
            result = StreamDecoder._base64_decode(result)
            if result is None:
                return ""
            
            # 5. Shift back (SHF)
            result = StreamDecoder._shift_back(result)
            
            return result
        except Exception:
            return ""

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
        return self.hdch_decode(parts)

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

        return [{
            "url"       : video_url,
            "name"      : source,
            "referer"   : url,
            "subtitles" : subtitles
        }]

    async def load_links(self, url: str) -> list[dict]:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        results = []
        for alternatif in secici.css("div.alternative-links"):
            lang_code = alternatif.css("::attr(data-lang)").get().upper()

            for link in alternatif.css("button.alternative-link"):
                source   = f"{link.css('::text').get().replace('(HDrip Xbet)', '').strip()} {lang_code}"
                video_id = link.css("::attr(data-video)").get()

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