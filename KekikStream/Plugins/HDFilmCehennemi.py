# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import kekik_cache, PluginBase, SearchResult, MovieInfo, ExtractResult, Subtitle
from parsel           import Selector
import random, string

class HDFilmCehennemi(PluginBase):
    name     = "HDFilmCehennemi"
    main_url = "https://www.hdfilmcehennemi.nl"

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