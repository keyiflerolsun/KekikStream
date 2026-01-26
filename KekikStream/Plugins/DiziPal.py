# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, Subtitle, ExtractResult, HTMLHelper

class DiziPal(PluginBase):
    name        = "DiziPal"
    language    = "tr"
    main_url    = "https://dizipal.cc"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "dizipal güncel, dizipal yeni ve gerçek adresi. dizipal en yeni dizi ve filmleri güvenli ve hızlı şekilde sunar."

    main_page   = {
        f"{main_url}/kategori/aile/page/"          : "Aile",
        f"{main_url}/kategori/aksiyon/page/"       : "Aksiyon",
        f"{main_url}/kategori/animasyon/page/"     : "Animasyon",
        f"{main_url}/kategori/belgesel/page/"      : "Belgesel",
        f"{main_url}/kategori/bilim-kurgu/page/"   : "Bilim Kurgu",
        f"{main_url}/kategori/dram/page/"          : "Dram",
        f"{main_url}/kategori/fantastik/page/"     : "Fantastik",
        f"{main_url}/kategori/gerilim/page/"       : "Gerilim",
        f"{main_url}/kategori/gizem/page/"         : "Gizem",
        f"{main_url}/kategori/komedi/page/"        : "Komedi",
        f"{main_url}/kategori/korku/page/"         : "Korku",
        f"{main_url}/kategori/macera/page/"        : "Macera",
        f"{main_url}/kategori/muzik/page/"         : "Müzik",
        f"{main_url}/kategori/romantik/page/"      : "Romantik",
        f"{main_url}/kategori/savas/page/"         : "Savaş",
        f"{main_url}/kategori/suc/page/"           : "Suç",
        f"{main_url}/kategori/tarih/page/"         : "Tarih",
        f"{main_url}/kategori/vahsi-bati/page/"    : "Vahşi Batı",
        f"{main_url}/kategori/yerli/page/"         : "Yerli",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}{page}/")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.grid div.post-item"):
            title  = secici.select_attr("a", "title", veri)
            href   = secici.select_attr("a", "href", veri)
            poster = secici.select_poster("div.poster img", veri)

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster) if poster else None,
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.grid div.post-item"):
            title  = secici.select_attr("a", "title", veri)
            href   = secici.select_attr("a", "href", veri)
            poster = secici.select_poster("div.poster img", veri)

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster) if poster else None,
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        poster      = self.fix_url(secici.select_attr("meta[property='og:image']", "content"))
        description = secici.select_attr("meta[property='og:description']", "content")
        title       = secici.select_text("h1")
        
        year         = secici.meta_value("Yapım Yılı")
        rating       = secici.meta_value("IMDB Puanı")
        duration_raw = secici.meta_value("Süre")
        if duration_raw:
            parts = duration_raw.split()
            saat = 0
            dakika = 0

            for p in parts:
                if "s" in p:
                    saat = int(p.replace("s", ""))
                elif "dk" in p:
                    dakika = int(p.replace("dk", ""))

            duration = saat * 60 + dakika
        else:
            duration = None
    
        tags   = secici.meta_list("Tür")
        actors = secici.meta_list("Oyuncular")
        if not actors:
            actors = secici.select_attrs("div.swiper-slide a", "title")

        if "/dizi/" in url:
            episodes = []
            for ep in secici.select("div.episode-item"):
                name = secici.select_text("h4 a", ep)
                href = secici.select_attr("a", "href", ep)
                link_title = secici.select_attr("a", "title", ep)
                
                h4_texts = secici.select_texts("h4", ep)
                text = h4_texts[1] if len(h4_texts) > 1 else (h4_texts[0] if h4_texts else "")

                full_text = f"{text} {link_title}" if link_title else text

                if name and href:
                    s, e = secici.extract_season_episode(full_text or "")
                    episodes.append(Episode(season=s, episode=e, title=name, url=self.fix_url(href)))

            return SeriesInfo(
                url=url, poster=poster.replace("https://test4test.online", self.main_url), title=title, description=description, tags=tags,
                rating=rating, year=year, duration=duration, episodes=episodes or None, actors=actors
            )
        
        return MovieInfo(
            url=url, poster=poster.replace("https://test4test.online", self.main_url), title=title, description=description, tags=tags,
            rating=rating, year=year, duration=duration, actors=actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        # Reset headers to get HTML response
        self.httpx.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })
        self.httpx.headers.pop("X-Requested-With", None)

        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        iframe = secici.select_attr("div.video-player-area iframe", "src") or secici.select_attr("div.responsive-player iframe", "src")
        if not iframe:
            return []

        results = []

        self.httpx.headers.update({"Referer": f"{self.main_url}/"})
        i_istek = await self.httpx.get(iframe)
        i_text  = i_istek.text

        # m3u link çıkar
        m3u_link = secici.regex_first(r'file:"([^"]+)"', target=i_text)
        if m3u_link:

            # Altyazıları çıkar
            sub_text = secici.regex_first(r'"subtitle":"([^"]+)"', target=i_text)
            subtitles = []
            if sub_text:
                if "," in sub_text:
                    for sub in sub_text.split(","):
                        lang = sub.split("[")[1].split("]")[0] if "[" in sub else "Türkçe"
                        sub_url = sub.replace(f"[{lang}]", "")
                        subtitles.append(Subtitle(name=lang, url=self.fix_url(sub_url)))
                else:
                    lang = sub_text.split("[")[1].split("]")[0] if "[" in sub_text else "Türkçe"
                    sub_url = sub_text.replace(f"[{lang}]", "")
                    subtitles.append(Subtitle(name=lang, url=self.fix_url(sub_url)))

            results.append(ExtractResult(
                name      = self.name,
                url       = m3u_link,
                referer   = f"{self.main_url}/",
                subtitles = subtitles
            ))
        else:
            # Extractor'a yönlendir
            data = await self.extract(iframe)
            if data:
                results.append(data)

        return results
