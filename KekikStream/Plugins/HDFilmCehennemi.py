# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import kekik_cache, PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, Subtitle
from parsel           import Selector
import random, string

class HDFilmCehennemi(PluginBase):
    name        = "HDFilmCehennemi"
    language    = "tr"
    main_url    = "https://www.hdfilmcehennemi.nl"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Türkiye'nin en hızlı hd film izleme sitesi"

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

    @kekik_cache(ttl=60*60)
    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}")
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

    @kekik_cache(ttl=60*60)
    async def search(self, query: str) -> list[SearchResult]:
        istek = await self.httpx.get(
            url     = f"{self.main_url}/search?q={query}",
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

    @kekik_cache(ttl=60*60)
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
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors,
            duration    = duration_minutes
        )
    
    def generate_random_cookie(self):
        return "".join(random.choices(string.ascii_letters + string.digits, k=16))

    @kekik_cache(ttl=15*60)
    async def load_links(self, url: str) -> list[str]:
        self._data.clear()

        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        lang_code = secici.css("div.alternative-links::attr(data-lang)").get().upper()
        buttons   = secici.css("div.alternative-links > button")

        link_list = []

        for button in buttons:
            source   = button.css("button.alternative-link::text").get().replace("(HDrip Xbet)", "").strip() + " " + lang_code
            video_id = button.css("button.alternative-link::attr(data-video)").get()

            istek = await self.httpx.get(
                url     = f"{self.main_url}/video/{video_id}/",
                headers = {
                    "Referer"          : f"{self.main_url}/", 
                    "X-Requested-With" : "fetch", 
                    "authority"        : f"{self.main_url}"
                }
            )

            data       = istek.json().get("data")
            secici     = Selector(data["html"])
            iframe_url = secici.css("iframe::attr(src)").get() or secici.css("iframe::attr(data-src)").get()

            if "?rapidrame_id=" in iframe_url:
                # https://hdfilmcehennemi.mobi/video/embed/uQcCR9nhaNz/?rapidrame_id=j4b4kvc0s24l\
                video_id = iframe_url.split("=")[1]
            else:
                # https://www.hdfilmcehennemi.nl/rplayer/j4b4kvc0s24l/
                video_id = iframe_url.split("/")[-1]

            # print(video_id)
            if(video_id):
               break

        # selected_quality: low
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

        video_url = istek.json().get("download_link")
        # print(video_url)

        self._data[self.fix_url(video_url)] = {
            "ext_name"  : f"{self.name} | Düşük Kalite",
            "name"      : "Düşük Kalite",
            "referer"   : f"https://cehennempass.pw/download/{video_id}",
            "subtitles" : []
        }

        # selected_quality: high
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

        video_url = istek.json().get("download_link")

        self._data[self.fix_url(video_url)] = {
            "ext_name"  : f"{self.name} | Yüksek Kalite",
            "name"      : "Yüksek Kalite",
            "referer"   : f"https://cehennempass.pw/download/{video_id}",
            "subtitles" : []
        }

        return list(self._data.keys())

    async def play(self, name: str, url: str, referer: str, subtitles: list[Subtitle]):
        extract_result = ExtractResult(name=name, url=url, referer=referer, subtitles=subtitles)
        self.media_handler.title = name
        if self.name not in self.media_handler.title:
            self.media_handler.title = f"{self.name} | {self.media_handler.title}"

        self.media_handler.play_media(extract_result)