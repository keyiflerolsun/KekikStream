# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, Subtitle, HTMLHelper
import base64

class KultFilmler(PluginBase):
    name        = "KultFilmler"
    language    = "tr"
    main_url    = "https://kultfilmler.net"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Kült Filmler özenle en iyi filmleri derler ve iyi bir altyazılı film izleme deneyimi sunmayı amaçlar. Reklamsız 1080P Altyazılı Film izle..."

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
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.col-md-12 div.movie-box"):
            title  = secici.select_attr("div.img img", "alt", veri)
            href   = secici.select_attr("a", "href", veri)
            poster = secici.select_attr("div.img img", "src", veri)

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster) if poster else None,
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movie-box"):
            title  = secici.select_attr("div.img img", "alt", veri)
            href   = secici.select_attr("a", "href", veri)
            poster = secici.select_attr("div.img img", "src", veri)

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

        title       = self.clean_title(secici.select_attr("div.film-bilgileri img", "alt") or secici.select_attr("[property='og:title']", "content"))
        poster      = self.fix_url(secici.select_attr("[property='og:image']", "content"))
        description = secici.select_text("div.description")
        tags        = secici.select_texts("ul.post-categories a")
        year        = secici.extract_year("li.release span a")
        duration    = int(secici.regex_first(r"(\d+)", secici.select_text("li.time span")) or 0)
        rating      = secici.regex_first(r"(\d+\.\d+|\d+)", secici.select_text("div.imdb-count"))
        actors      = secici.select_texts("div.actors a")

        if "/dizi/" in url:
            episodes = []
            for bolum in secici.select("div.episode-box"):
                href       = secici.select_attr("div.name a", "href", bolum)
                ssn_detail = secici.select_text("span.episodetitle", bolum) or ""
                ep_detail  = secici.select_text("span.episodetitle b", bolum) or ""
                if href:
                    s, e = secici.extract_season_episode(f"{ssn_detail} {ep_detail}")
                    name = f"{ssn_detail} - {ep_detail}".strip(" -")
                    episodes.append(Episode(season=s or 1, episode=e or 1, title=name, url=self.fix_url(href)))

            return SeriesInfo(
                url=url, poster=poster, title=title or "Bilinmiyor", description=description,
                tags=tags, year=str(year) if year else None, actors=actors, rating=rating, episodes=episodes
            )

        return MovieInfo(
            url=url, poster=poster, title=title or "Bilinmiyor", description=description,
            tags=tags, year=str(year) if year else None, rating=rating, actors=actors, duration=duration
        )

    def _get_iframe(self, source_code: str) -> str:
        """Base64 kodlu iframe'i çözümle"""
        atob = HTMLHelper(source_code).regex_first(r"PHA\+[0-9a-zA-Z+/=]*")
        if not atob:
            return ""

        # Padding düzelt
        padding = 4 - len(atob) % 4
        if padding < 4:
            atob = atob + "=" * padding

        try:
            decoded = base64.b64decode(atob).decode("utf-8")
            secici  = HTMLHelper(decoded)
            iframe_src = secici.select_attr("iframe", "src")
            return self.fix_url(iframe_src) if iframe_src else ""
        except Exception:
            return ""

    def _extract_subtitle_url(self, source_code: str) -> str | None:
        """Altyazı URL'sini çıkar"""
        return HTMLHelper(source_code).regex_first(r"(https?://[^\s\"]+\.srt)")

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        iframes = set()

        # Ana iframe
        main_frame = self._get_iframe(istek.text)
        if main_frame:
            iframes.add(main_frame)

        # Alternatif player'lar
        for player in secici.select("div.container#player"):
            iframe_src = secici.select_attr("iframe", "src", player)
            alt_iframe = self.fix_url(iframe_src) if iframe_src else None
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
                m3u_match    = HTMLHelper(iframe_istek.text).regex_first(r'file:"([^"]+)"')

                if m3u_match:
                    results.append(ExtractResult(
                        name      = "VidMoly",
                        url       = m3u_match,
                        referer   = self.main_url,
                        subtitles = []
                    ))
                    continue

            # Altyazı çıkar
            subtitle_url = self._extract_subtitle_url(url)
            if subtitle_url:
                subtitles.append(Subtitle(name="Türkçe", url=subtitle_url))

            data = await self.extract(iframe)
            if data:
                # ExtractResult objesi immutable, yeni bir kopya oluştur
                updated_data = data.model_copy(update={"subtitles": subtitles}) if subtitles else data
                results.append(updated_data)

        return results
