# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, Subtitle, ExtractResult, HTMLHelper
from Kekik.Sifreleme   import Packer, StreamDecoder
import random, string

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
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.section-content a.poster"):
            title = secici.select_text("strong.poster-title", veri)
            href = veri.attrs.get("href")
            poster = secici.select_attr("img", "data-src", veri)

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
            secici = HTMLHelper(veri)
            title  = secici.select_text("h4.title")
            href   = secici.select_attr("a", "href")
            poster = secici.select_attr("img", "data-src") or secici.select_attr("img", "src")

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster).replace("/thumb/", "/list/") if poster else None,
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url, headers = {"Referer": f"{self.main_url}/"})
        secici = HTMLHelper(istek.text)

        title = secici.select_text("h1.section-title") or ""

        poster = secici.select_attr("aside.post-info-poster img.lazyload", "data-src") or ""
        poster = poster.strip()

        description = secici.select_text("article.post-info-content > p") or ""

        tags = secici.select_all_text("div.post-info-genres a")

        rating = secici.select_text("div.post-info-imdb-rating span") or ""

        year = secici.select_text("div.post-info-year-country a") or ""

        actors = secici.select_all_text("div.post-info-cast a > strong")

        duration_str = secici.select_text("div.post-info-duration") or "0"
        duration_str = duration_str.replace("dakika", "").strip()

        try:
            duration_val = HTMLHelper(duration_str).regex_first(r'\d+')
            duration_minutes = int(duration_val) if duration_val else 0
        except Exception:
            duration_minutes = 0

        # Dizi mi film mi kontrol et (Kotlin referansı: div.seasons kontrolü)
        is_series = len(secici.select("div.seasons")) > 0

        if is_series:
            episodes = []
            for ep in secici.select("div.seasons-tab-content a"):
                ep_name = secici.select_text("h4", ep)
                ep_href = ep.attrs.get("href")

                if ep_name and ep_href:
                    # Regex ile sezon ve bölüm numarası çıkar
                    ep_val = HTMLHelper(ep_name).regex_first(r'(\d+)\.\s*Bölüm')
                    sz_val = HTMLHelper(ep_name).regex_first(r'(\d+)\.\s*Sezon')
                    ep_num = int(ep_val) if ep_val and ep_val.isdigit() else 1
                    sz_num = int(sz_val) if sz_val and sz_val.isdigit() else 1
                    
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

    def _extract_from_json_ld(self, html: str) -> str | None:
        """JSON-LD script tag'inden contentUrl'i çıkar (Kotlin versiyonundaki gibi)"""
        # Önce JSON-LD'den dene
        json_ld = HTMLHelper(html).regex_first(r'(?s)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>')
        if json_ld:
            try:
                import json
                data = json.loads(json_ld.strip())
                if content_url := data.get("contentUrl"):
                    if content_url.startswith("http"):
                        return content_url
            except Exception:
                # Regex ile contentUrl'i çıkarmayı dene
                content_url = HTMLHelper(html).regex_first(r'"contentUrl"\s*:\s*"([^"]+)"')
                if content_url and content_url.startswith("http"):
                    return content_url
        return None

    async def invoke_local_source(self, iframe: str, source: str, url: str):
        self.httpx.headers.update({
            "Referer": f"{self.main_url}/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0"
        })
        istek = await self.httpx.get(iframe)

        if not istek.text:
            return await self.cehennempass(iframe.split("/")[-1])

        # Önce JSON-LD'den dene (Kotlin versiyonu gibi - daha güvenilir)
        video_url = self._extract_from_json_ld(istek.text)

        # Fallback: Packed JavaScript'ten çıkar
        if not video_url:
            # eval(function...) içeren packed script bul
            eval_script = HTMLHelper(istek.text).regex_first(r'(eval\(function[\s\S]+)')
            if not eval_script:
                return await self.cehennempass(iframe.split("/")[-1])

            try:
                unpacked = Packer.unpack(eval_script)
                video_url = StreamDecoder.extract_stream_url(unpacked)
            except Exception:
                return await self.cehennempass(iframe.split("/")[-1])
        
        if not video_url:
            return await self.cehennempass(iframe.split("/")[-1])

        subtitles = []
        try:
            sub_data = istek.text.split("tracks: [")[1].split("]")[0]
            for file_url, lang in HTMLHelper(sub_data).regex_all(r'(?s)file":"([^\\"]+)".*?"language":"([^\\"]+)"'):
                subtitles.append(Subtitle(
                    name = lang.upper(),
                    url  = self.fix_url(file_url.replace("\\", "")),
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
        secici = HTMLHelper(istek.text)

        results = []
        for alternatif in secici.select("div.alternative-links"):
            lang_code = alternatif.attrs.get("data-lang", "").upper()

            for link in secici.select("button.alternative-link", alternatif):
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

                iframe = HTMLHelper(api_get.text).regex_first(r'data-src=\\\"([^\"]+)')
                iframe = iframe.replace("\\", "") if iframe else None

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