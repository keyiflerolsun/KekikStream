# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, Subtitle
from selectolax.parser import HTMLParser
import re, base64

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
        secici = HTMLParser(istek.text)

        results = []
        for veri in secici.css("div.col-md-12 div.movie-box"):
            img_el  = veri.css_first("div.img img")
            link_el = veri.css_first("a")

            title  = img_el.attrs.get("alt") if img_el else None
            href   = link_el.attrs.get("href") if link_el else None
            poster = img_el.attrs.get("src") if img_el else None

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
        secici = HTMLParser(istek.text)

        results = []
        for veri in secici.css("div.movie-box"):
            img_el  = veri.css_first("div.img img")
            link_el = veri.css_first("a")

            title  = img_el.attrs.get("alt") if img_el else None
            href   = link_el.attrs.get("href") if link_el else None
            poster = img_el.attrs.get("src") if img_el else None

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster) if poster else None,
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)

        film_img = secici.css_first("div.film-bilgileri img")
        og_title = secici.css_first("[property='og:title']")
        og_image = secici.css_first("[property='og:image']")

        title       = (film_img.attrs.get("alt") if film_img else None) or (og_title.attrs.get("content") if og_title else None)
        poster      = self.fix_url(og_image.attrs.get("content")) if og_image else None

        desc_el     = secici.css_first("div.description")
        description = desc_el.text(strip=True) if desc_el else None

        tags = [a.text(strip=True) for a in secici.css("ul.post-categories a") if a.text(strip=True)]

        # HTML analizine göre güncellenen alanlar
        year_el = secici.css_first("li.release span a")
        year    = year_el.text(strip=True) if year_el else None

        time_el = secici.css_first("li.time span")
        duration = None
        if time_el:
            time_text = time_el.text(strip=True)
            dur_match = re.search(r"(\d+)", time_text)
            duration  = dur_match.group(1) if dur_match else None

        rating_el = secici.css_first("div.imdb-count")
        rating    = rating_el.text(strip=True) if rating_el else None

        actors = [a.text(strip=True) for a in secici.css("div.actors a") if a.text(strip=True)]

        # Dizi mi kontrol et
        if "/dizi/" in url:
            episodes = []
            for bolum in secici.css("div.episode-box"):
                name_link = bolum.css_first("div.name a")
                ep_href   = name_link.attrs.get("href") if name_link else None

                ssn_el = bolum.css_first("span.episodetitle")
                ssn_detail = ssn_el.text(strip=True) if ssn_el else ""

                ep_b_el = bolum.css_first("span.episodetitle b")
                ep_detail = ep_b_el.text(strip=True) if ep_b_el else ""

                ep_name = f"{ssn_detail} - {ep_detail}"

                if ep_href:
                    ep_season  = re.search(r"(\d+)\.", ssn_detail)
                    ep_episode = re.search(r"(\d+)\.", ep_detail)

                    episodes.append(Episode(
                        season  = int(ep_season[1]) if ep_season else 1,
                        episode = int(ep_episode[1]) if ep_episode else 1,
                        title   = ep_name.strip(" -"),
                        url     = self.fix_url(ep_href),
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
            secici  = HTMLParser(decoded)
            iframe_el = secici.css_first("iframe")
            return self.fix_url(iframe_el.attrs.get("src")) if iframe_el else ""
        except Exception:
            return ""

    def _extract_subtitle_url(self, source_code: str) -> str | None:
        """Altyazı URL'sini çıkar"""
        match = re.search(r"(https?://[^\s\"]+\.srt)", source_code)
        return match[1] if match else None

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)

        iframes = set()

        # Ana iframe
        main_frame = self._get_iframe(istek.text)
        if main_frame:
            iframes.add(main_frame)

        # Alternatif player'lar
        for player in secici.css("div.container#player"):
            iframe_el = player.css_first("iframe")
            alt_iframe = self.fix_url(iframe_el.attrs.get("src")) if iframe_el else None
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
                    results.append(ExtractResult(
                        name      = "VidMoly",
                        url       = m3u_match[1],
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
