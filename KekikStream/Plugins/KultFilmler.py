# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, Subtitle
from parsel import Selector
import re, base64

class KultFilmler(PluginBase):
    name        = "KultFilmler"
    language    = "tr"
    main_url    = "https://kultfilmler.net"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Kült film ve dizi izleme sitesi."

    main_page   = {
        f"{main_url}/category/aile-filmleri-izle"       : "Aile",
        f"{main_url}/category/aksiyon-filmleri-izle"    : "Aksiyon",
        f"{main_url}/category/animasyon-filmleri-izle"  : "Animasyon",
        f"{main_url}/category/belgesel-izle"            : "Belgesel",
        f"{main_url}/category/bilim-kurgu-filmleri-izle": "Bilim Kurgu",
        f"{main_url}/category/biyografi-filmleri-izle"  : "Biyografi",
        f"{main_url}/category/dram-filmleri-izle"       : "Dram",
        f"{main_url}/category/fantastik-filmleri-izle"  : "Fantastik",
        f"{main_url}/category/gerilim-filmleri-izle"    : "Gerilim",
        f"{main_url}/category/gizem-filmleri-izle"      : "Gizem",
        f"{main_url}/category/kara-filmleri-izle"       : "Kara Film",
        f"{main_url}/category/kisa-film-izle"           : "Kısa Metraj",
        f"{main_url}/category/komedi-filmleri-izle"     : "Komedi",
        f"{main_url}/category/korku-filmleri-izle"      : "Korku",
        f"{main_url}/category/macera-filmleri-izle"     : "Macera",
        f"{main_url}/category/muzik-filmleri-izle"      : "Müzik",
        f"{main_url}/category/polisiye-filmleri-izle"   : "Polisiye",
        f"{main_url}/category/romantik-filmleri-izle"   : "Romantik",
        f"{main_url}/category/savas-filmleri-izle"      : "Savaş",
        f"{main_url}/category/suc-filmleri-izle"        : "Suç",
        f"{main_url}/category/tarih-filmleri-izle"      : "Tarih",
        f"{main_url}/category/yerli-filmleri-izle"      : "Yerli",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        results = []
        for veri in secici.css("div.col-md-12 div.movie-box"):
            title  = veri.css("div.img img::attr(alt)").get()
            href   = self.fix_url(veri.css("a::attr(href)").get())
            poster = self.fix_url(veri.css("div.img img::attr(src)").get())

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = href,
                    poster   = poster,
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}?s={query}")
        secici = Selector(istek.text)

        results = []
        for veri in secici.css("div.movie-box"):
            title  = veri.css("div.img img::attr(alt)").get()
            href   = self.fix_url(veri.css("a::attr(href)").get())
            poster = self.fix_url(veri.css("div.img img::attr(src)").get())

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = href,
                    poster = poster,
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        title       = secici.css("div.film-bilgileri img::attr(alt)").get() or secici.css("[property='og:title']::attr(content)").get()
        poster      = self.fix_url(secici.css("[property='og:image']::attr(content)").get())
        description = secici.css("div.description::text").get()
        tags        = secici.css("ul.post-categories a::text").getall()
        # HTML analizine göre güncellenen alanlar
        year        = secici.css("li.release span a::text").get()
        duration    = secici.css("li.time span::text").re_first(r"(\d+)")
        rating      = secici.css("div.imdb-count::text").get()
        actors      = secici.css("div.actors a::text").getall()
        if rating:
            rating = rating.strip()

        # Dizi mi kontrol et
        if "/dizi/" in url:
            episodes = []
            for bolum in secici.css("div.episode-box"):
                ep_href   = self.fix_url(bolum.css("div.name a::attr(href)").get())
                ssn_detail = bolum.css("span.episodetitle::text").get() or ""
                ep_detail  = bolum.css("span.episodetitle b::text").get() or ""
                ep_name    = f"{ssn_detail} - {ep_detail}"

                if ep_href:
                    ep_season  = re.search(r"(\d+)\.", ssn_detail)
                    ep_episode = re.search(r"(\d+)\.", ep_detail)

                    episodes.append(Episode(
                        season  = int(ep_season[1]) if ep_season else 1,
                        episode = int(ep_episode[1]) if ep_episode else 1,
                        title   = ep_name.strip(" -"),
                        url     = ep_href,
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
                episodes    = episodes,
            )

        return MovieInfo(
            url         = url,
            poster      = poster,
            title       = self.clean_title(title) if title else "",
            description = description,
            tags        = tags,
            year        = year,
            rating      = rating,
            actors      = actors,
            duration    = int(duration) if duration else None,
        )

    def _get_iframe(self, source_code: str) -> str:
        """Base64 kodlu iframe'i çözümle"""
        atob_match = re.search(r"PHA\+[0-9a-zA-Z+/=]*", source_code)
        if not atob_match:
            return ""

        atob = atob_match.group()

        # Padding düzelt
        padding = 4 - len(atob) % 4
        if padding < 4:
            atob = atob + "=" * padding

        try:
            decoded = base64.b64decode(atob).decode("utf-8")
            secici  = Selector(text=decoded)
            return self.fix_url(secici.css("iframe::attr(src)").get()) or ""
        except Exception:
            return ""

    def _extract_subtitle_url(self, source_code: str) -> str | None:
        """Altyazı URL'sini çıkar"""
        match = re.search(r"(https?://[^\s\"]+\.srt)", source_code)
        return match[1] if match else None

    async def load_links(self, url: str) -> list[dict]:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        iframes = set()

        # Ana iframe
        main_frame = self._get_iframe(istek.text)
        if main_frame:
            iframes.add(main_frame)

        # Alternatif player'lar
        for player in secici.css("div.container#player"):
            alt_iframe = self.fix_url(player.css("iframe::attr(src)").get())
            if alt_iframe:
                alt_istek = await self.httpx.get(alt_iframe)
                alt_frame = self._get_iframe(alt_istek.text)
                if alt_frame:
                    iframes.add(alt_frame)

        results = []

        for iframe in iframes:
            subtitles = []

            # VidMoly özel işleme
            if "vidmoly" in iframe:
                headers = {
                    "User-Agent"     : "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
                    "Sec-Fetch-Dest" : "iframe"
                }
                iframe_istek = await self.httpx.get(iframe, headers=headers)
                m3u_match    = re.search(r'file:"([^"]+)"', iframe_istek.text)

                if m3u_match:
                    results.append({
                        "name"      : "VidMoly",
                        "url"       : m3u_match[1],
                        "referer"   : self.main_url,
                        "subtitles" : []
                    })
                    continue

            # Altyazı çıkar
            subtitle_url = self._extract_subtitle_url(url)
            if subtitle_url:
                subtitles.append(Subtitle(name="Türkçe", url=subtitle_url))

            extractor = self.ex_manager.find_extractor(iframe)
            results.append({
                "name"      : extractor.name if extractor else "Player",
                "url"       : iframe,
                "referer"   : f"{self.main_url}/",
                "subtitles" : subtitles
            })

        return results
