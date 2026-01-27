# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, Subtitle, ExtractResult, HTMLHelper
from Kekik.Sifreleme  import Packer, StreamDecoder
import random, string, json, asyncio, contextlib

class HDFilmCehennemi(PluginBase):
    name        = "HDFilmCehennemi"
    language    = "tr"
    main_url    = "https://www.hdfilmcehennemi.nl"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Türkiye'nin en hızlı hd film izleme sitesi. Tek ve gerçek hdfilmcehennemi sitesi."

    main_page   = {
        f"{main_url}"                                               : "Yeni Eklenen Filmler",
        f"{main_url}/yabancidiziizle-5"                             : "Yeni Eklenen Diziler",
        f"{main_url}/dil/turkce-dublajli-film-izleyin-5"            : "Türkçe Dublaj Filmler",
        f"{main_url}/dil/turkce-altyazili-filmleri-izleme-sitesi-3" : "Türkçe Altyazılı Filmler",
        f"{main_url}/category/tavsiye-filmler-izle3"                : "Tavsiye Filmler",
        f"{main_url}/imdb-7-puan-uzeri-filmler-2"                   : "IMDB 7+ Filmler",
        f"{main_url}/en-cok-yorumlananlar-2"                        : "En Çok Yorumlananlar",
        f"{main_url}/en-cok-begenilen-filmleri-izle-4"              : "En Çok Beğenilenler",
        f"{main_url}/serifilmlerim-4"                               : "Seri Filmler",
        f"{main_url}/category/nette-ilk-filmler"                    : "Nette İlk Filmler",
        f"{main_url}/category/4k-film-izle-5"                       : "4K Filmler",
        f"{main_url}/category/1080p-hd-film-izle-5"                 : "1080p Filmler",
        f"{main_url}/category/amazon-yapimlarini-izle"              : "Amazon Yapımları",
        f"{main_url}/category/netflix-yapimlari-izle"               : "Netflix Yapımları",
        f"{main_url}/category/marvel-yapimlarini-izle-5"            : "Marvel Filmleri",
        f"{main_url}/category/dc-yapimlarini-izle-1"                : "DC Filmleri",
        f"{main_url}/tur/aile-filmleri-izleyin-7"                   : "Aile Filmleri",
        f"{main_url}/tur/aksiyon-filmleri-izleyin-6"                : "Aksiyon Filmleri",
        f"{main_url}/tur/animasyon-filmlerini-izleyin-5"            : "Animasyon Filmleri",
        f"{main_url}/tur/belgesel-filmlerini-izle-2"                : "Belgesel Filmleri",
        f"{main_url}/tur/bilim-kurgu-filmlerini-izleyin-5"          : "Bilim Kurgu Filmleri",
        f"{main_url}/tur/biyografi-filmleri-izle-3"                 : "Biyografi Filmleri",
        f"{main_url}/tur/dram-filmlerini-izle-2"                    : "Dram Filmleri",
        f"{main_url}/tur/fantastik-filmlerini-izleyin-3"            : "Fantastik Filmleri",
        f"{main_url}/tur/gerilim-filmlerini-izle-2"                 : "Gerilim Filmleri",
        f"{main_url}/tur/gizem-filmleri-izle-3"                     : "Gizem Filmleri",
        f"{main_url}/tur/komedi-filmlerini-izleyin-2"               : "Komedi Filmleri",
        f"{main_url}/tur/korku-filmlerini-izle-5"                   : "Korku Filmleri",
        f"{main_url}/tur/macera-filmlerini-izleyin-4"               : "Macera Filmleri",
        f"{main_url}/tur/muzik-filmlerini-izle-844"                 : "Müzik Filmleri",
        f"{main_url}/tur/polisiye-filmleri-izle"                    : "Polisiye Filmleri",
        f"{main_url}/tur/romantik-filmleri-izle-3"                  : "Romantik Filmleri",
        f"{main_url}/tur/savas-filmleri-izle-5"                     : "Savaş Filmleri",
        f"{main_url}/tur/spor-filmleri-izle-3"                      : "Spor Filmleri",
        f"{main_url}/tur/suc-filmleri-izle-3"                       : "Suç Filmleri",
        f"{main_url}/tur/tarih-filmleri-izle-5"                     : "Tarih Filmleri",
        f"{main_url}/tur/western-filmleri-izle-3"                   : "Western Filmleri"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}", follow_redirects=True)
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.section-content a.poster"):
            title  = secici.select_text("strong.poster-title", veri)
            href   = veri.attrs.get("href")
            poster = secici.select_attr("img", "data-src", veri)

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
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

        title       = self.clean_title(secici.select_text("h1.section-title"))
        poster      = secici.select_poster("aside.post-info-poster img.lazyload")
        description = secici.select_text("article.post-info-content > p")
        tags        = secici.select_texts("div.post-info-genres a")
        rating      = secici.select_text("div.post-info-imdb-rating span")
        rating      = rating.split("(")[0] if rating else None
        year        = secici.select_text("div.post-info-year-country a")
        actors      = secici.select_texts("div.post-info-cast a > strong")
        duration    = int(secici.regex_first(r"(\d+)", secici.select_text("div.post-info-duration")) or 0)

        # Dizi mi film mi kontrol et
        ep_links = secici.select("div.seasons-tab-content a")

        if ep_links:
            episodes = []
            for ep in ep_links:
                name = secici.select_text("h4", ep)
                href = ep.attrs.get("href")
                if name and href:
                    s, e = secici.extract_season_episode(name)
                    episodes.append(Episode(
                        season  = s or 1,
                        episode = e or 1,
                        title   = name,
                        url     = self.fix_url(href)
                    ))

            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = title,
                description = description,
                tags        = tags,
                rating      = rating,
                year        = year,
                actors      = actors,
                episodes    = episodes
            )

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors,
            duration    = duration
        )

    def generate_random_cookie(self):
        return "".join(random.choices(string.ascii_letters + string.digits, k=16))

    async def cehennempass(self, video_id: str, name_prefix: str = "", subtitles: list[Subtitle] = None) -> list[ExtractResult]:
        results = []
        subs    = subtitles or []

        for quality, label in [("low", "Düşük Kalite"), ("high", "Yüksek Kalite")]:
            with contextlib.suppress(Exception):
                istek = await self.httpx.post(
                    url     = "https://cehennempass.pw/process_quality_selection.php",
                    headers = {
                        "Referer"          : f"https://cehennempass.pw/download/{video_id}", 
                        "X-Requested-With" : "fetch", 
                        "authority"        : "cehennempass.pw",
                        "Cookie"           : f"PHPSESSID={self.generate_random_cookie()}"
                    },
                    data    = {"video_id": video_id, "selected_quality": quality},
                )
                if video_url := istek.json().get("download_link"):
                    results.append(ExtractResult(
                        url       = self.fix_url(video_url),
                        name      = f"{name_prefix} | {label}" if name_prefix else label,
                        referer   = f"https://cehennempass.pw/download/{video_id}",
                        subtitles = subs
                    ))

        return results

    def _extract_video_url(self, html: str) -> str | None:
        """Video URL'sini çeşitli yöntemlerle (JSON-LD, Regex, Packer) çıkarır"""
        secici = HTMLHelper(html)

        # 1. JSON-LD'den dene
        json_ld = secici.regex_first(r'(?s)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>')
        if json_ld:
            with contextlib.suppress(Exception):
                data = json.loads(json_ld.strip())
                if content_url := data.get("contentUrl"):
                    if content_url.startswith("http"):
                        return content_url

        # 2. Regex ile contentUrl dene
        content_url = secici.regex_first(r'"contentUrl"\s*:\s*"([^"]+)"')
        if content_url and content_url.startswith("http"):
            return content_url

        # 3. Packed JavaScript (eval(function...)) dene
        if eval_script := secici.regex_first(r'(eval\(function[\s\S]+)'):
            with contextlib.suppress(Exception):
                unpacked = Packer.unpack(eval_script)
                return StreamDecoder.extract_stream_url(unpacked)

        return None

    def _extract_subtitles(self, html: str) -> list[Subtitle]:
        """HTML içeriğinden çeşitli formatlardaki altyazıları çıkarır"""
        subtitles = []
        secici    = HTMLHelper(html)

        # 1. JWPlayer / Plyr / Generic JS Object (tracks: [ ... ])
        if match := secici.regex_first(r'tracks\s*:\s*(\[[^\]]+\])'):
            # JSON parse denemesi
            with contextlib.suppress(Exception):
                track_data = json.loads(match)
                for t in track_data:
                    if file_url := t.get("file"):
                        label = t.get("label") or t.get("language") or "TR"
                        if t.get("kind", "captions") in ["captions", "subtitles"]: 
                            subtitles.append(Subtitle(name=label.upper(), url=self.fix_url(file_url)))
                return subtitles # JSON başarılıysa dön

            # Regex fallback
            for m in HTMLHelper(match).regex_all(r'file\s*:\s*["\']([^"\']+)["\'].*?(?:label|language)\s*:\s*["\']([^"\']+)["\']'):
                file_url, lang = m
                subtitles.append(Subtitle(name=lang.upper(), url=self.fix_url(file_url.replace("\\", ""))))

        # 2. PlayerJS (subtitle: "url,name;url,name")
        if not subtitles:
            if sub_str := secici.regex_first(r'subtitle\s*:\s*["\']([^"\']+)["\']'):
                for sub_item in sub_str.split(";"):
                    if "," in sub_item:
                        # [TR]url,[EN]url gibi yapılar için split mantığı
                        # Basitçe virgülle ayırıp http kontrolü yapalım
                        parts = sub_item.split(",")
                        u, n  = (parts[0], parts[1]) if "http" in parts[0] else (parts[1], parts[0])
                        subtitles.append(Subtitle(name=n.strip(), url=self.fix_url(u.strip())))
                    elif "http" in sub_item:
                        subtitles.append(Subtitle(name="TR", url=self.fix_url(sub_item.strip())))

        # 3. HTML5 Track Tags
        if not subtitles:
            for track in secici.select("track[kind='captions'], track[kind='subtitles']"):
                src   = track.attrs.get("src")
                label = track.attrs.get("label") or track.attrs.get("srclang") or "TR"
                if src:
                    subtitles.append(Subtitle(name=label.upper(), url=self.fix_url(src)))

        return subtitles

    async def invoke_local_source(self, iframe: str, source: str, url: str) -> list[ExtractResult]:
        istek = await self.httpx.get(
            url     = iframe,
            headers = {
                "User-Agent"       : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "X-Requested-With" : "XMLHttpRequest",
                "Referer"          : self.main_url + "/" 
            }
        )

        # ID'yi güvenli al
        video_id = iframe.rstrip("/").split("/")[-1]

        # Boş yanıt kontrolü
        if not istek.text or len(istek.text) < 50:
            return await self.cehennempass(video_id, source, [])

        # 1. Altyazıları Çıkar
        subtitles = self._extract_subtitles(istek.text)

        # 2. Video URL'sini Çıkar
        video_url = self._extract_video_url(istek.text)

        # 3. Eğer Video URL yoksa CehennemPass'a git
        if not video_url:
            return await self.cehennempass(video_id, source, subtitles)

        return [ExtractResult(
            url       = video_url,
            name      = source,
            referer   = url,
            subtitles = subtitles
        )]

    async def _get_video_source(self, video_id: str, source_name: str, referer: str) -> list[ExtractResult]:
        try:
            api_get = await self.httpx.get(
                url     = f"{self.main_url}/video/{video_id}/",
                headers = {
                    "Content-Type"     : "application/json",
                    "X-Requested-With" : "fetch",
                    "Referer"          : referer,
                }
            )

            # JSON Parse (Daha güvenli)
            # Response: {"success": true, "data": {"html": "<iframe class=\"rapidrame\" data-src=\"...\" ...></iframe>"}}
            try:
                json_data    = api_get.json()
                html_content = json_data.get("data", {}).get("html", "")
                iframe       = HTMLHelper(html_content).select_attr("iframe", "data-src")
            except:
                # RegEx fallback
                iframe = HTMLHelper(api_get.text).regex_first(r'data-src=\\\"([^\"]+)')
                iframe = iframe.replace("\\", "") if iframe else None

            if not iframe:
                return []

            # mobi URL'si varsa direkt kullan
            if "mobi" in iframe: # m.hdfilmcehennemi.nl veya /mobi/
                iframe = iframe.split("?")[0]
            # rapidrame ve query varsa
            elif "rapidrame" in iframe and "?rapidrame_id=" in iframe:
                # /rplayer/ID/ formatına çevir
                 rap_id = iframe.split('?rapidrame_id=')[1]
                 iframe = f"{self.main_url}/rplayer/{rap_id}"

            return await self.invoke_local_source(iframe, source_name, referer)
        except Exception:
            return []

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        sources = []
        for alternatif in secici.select("div.alternative-links"):
            lang_code = alternatif.attrs.get("data-lang", "").upper()

            # Dil metnini bul
            if lang_code:
                if lang_btn := secici.select_first(f"button.language-link[data-lang='{lang_code.lower()}']"):
                    lang_text = lang_btn.text(strip=True)
                    # "DUAL (Türkçe Dublaj & Altyazılı)" -> "DUAL" yap, diğerleri aynen kalsın
                    if "DUAL" in lang_text:
                        lang_code = "DUAL"
                    else:
                        lang_code = lang_text

            for link in secici.select("button.alternative-link", alternatif):
                source_text = link.text(strip=True).replace('(HDrip Xbet)', '').strip()
                source_name = f"{lang_code} | {source_text}".strip()
                video_id    = link.attrs.get("data-video")

                if video_id:
                    sources.append((video_id, source_name, url))

        tasks = []
        for vid, name, ref in sources:
            tasks.append(self._get_video_source(vid, name, ref))

        return [item for sublist in await asyncio.gather(*tasks) for item in sublist]
