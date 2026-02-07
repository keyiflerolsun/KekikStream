# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, Subtitle, HTMLHelper
import base64, asyncio, contextlib

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
                    poster   = self.fix_url(poster),
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
                    poster = self.fix_url(poster),
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
                url         = url,
                poster      = poster,
                title       = title,
                description = description,
                tags        = tags,
                year        = year,
                actors      = actors,
                rating      = rating,
                episodes    = episodes
            )

        return MovieInfo(
            url         = url,
            poster      = poster,
            title       = title,
            description = description,
            tags        = tags,
            year        = year,
            rating      = rating,
            actors      = actors,
            duration    = duration
        )

    def _decode_iframe(self, content: str) -> str | None:
        """Base64 kodlanmış iframe verisini çözer"""
        match = HTMLHelper(content).regex_first(r"PHA\+[0-9a-zA-Z+/=]*")
        if not match:
            return None

        # Base64 Padding Fix
        pad = len(match) % 4
        if pad:
            match += "=" * (4 - pad)

        try:
            decoded = base64.b64decode(match).decode("utf-8")
            src = HTMLHelper(decoded).select_attr("iframe", "src")
            return self.fix_url(src) if src else None
        except Exception:
            return None

    async def _resolve_alt_page(self, url: str, title: str) -> tuple[str | None, str]:
        """Alternatif sayfa kaynak kodunu indirip iframe'i bulur"""
        try:
            res = await self.httpx.get(url)
            return self._decode_iframe(res.text), title
        except Exception:
            return None, title

    async def _extract_stream(self, iframe_url: str, title: str, subtitles: list[Subtitle]) -> list[ExtractResult]:
        """Iframe üzerinden stream linklerini ayıklar"""
        results = []

        # 1. VidMoly Özel Çözümleme(M3U)
        if "vidmoly" in iframe_url:
            with contextlib.suppress(Exception):
                res = await self.httpx.get(
                    url     = iframe_url,
                    headers = {
                        "User-Agent"     : "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
                        "Sec-Fetch-Dest" : "iframe"
                    }
                )
                m3u = HTMLHelper(res.text).regex_first(r'file:"([^"]+)"')

                if m3u:
                    results.append(ExtractResult(
                        name      = title or "VidMoly",
                        url       = m3u,
                        referer   = self.main_url,
                        subtitles = subtitles
                    ))

            return results

        # 2. Genel Extractor Kullanımı
        with contextlib.suppress(Exception):
            extracted = await self.extract(iframe_url)
            if not extracted:
                return []

            items = extracted if isinstance(extracted, list) else [extracted]
            for item in items:
                # İsim ve altyazı bilgilerini güncelle
                # Orijinal extractor ismini ezmek için title kullan
                if title:
                    item.name = title

                # Varsa altyazıları ekle
                if subtitles:
                     # Copy update daha güvenli (Pydantic model)
                    if hasattr(item, "model_copy"):
                        item = item.model_copy(update={"subtitles": subtitles})
                    else:
                        item.subtitles = subtitles

                results.append(item)

        return results

    async def load_links(self, url: str) -> list[ExtractResult]:
        response = await self.httpx.get(url)
        source   = response.text
        helper   = HTMLHelper(source)

        # Altyazı Bul
        sub_url   = helper.regex_first(r"(https?://[^\s\"]+\.srt)")
        subtitles = [Subtitle(name="Türkçe", url=sub_url)] if sub_url else []

        # İşlenecek kaynakları topla: (Iframe_URL, Başlık)
        sources = []

        # A) Ana Player
        main_iframe = self._decode_iframe(source)
        if main_iframe:
            p_name = helper.select_text("div.parts-middle div.part.active div.part-name") or None
            p_lang = helper.select_attr("div.parts-middle div.part.active div.part-lang span", "title")
            full_title = f"{p_name} | {p_lang}" if p_lang else p_name
            sources.append((main_iframe, full_title))

        # B) Alternatif Playerlar (Link Çözümleme Gerektirir)
        alt_tasks = []
        for link in helper.select("div.parts-middle a.post-page-numbers"):
            href = link.attrs.get("href")
            if not href:
                continue

            a_name     = helper.select_text("div.part-name", link) or "Alternatif"
            a_lang     = helper.select_attr("div.part-lang span", "title", link)
            full_title = f"{a_name} | {a_lang}" if a_lang else a_name

            alt_tasks.append(self._resolve_alt_page(self.fix_url(href), full_title))

        if alt_tasks:
            resolved_alts = await asyncio.gather(*alt_tasks)
            for iframe, title in resolved_alts:
                if iframe:
                    sources.append((iframe, title))

        # 3. Tüm kaynakları paralel işle (Extract)
        if not sources:
            return []

        extract_tasks = [
            self._extract_stream(iframe, title, subtitles)
                for iframe, title in sources
        ]

        results_groups = await asyncio.gather(*extract_tasks)

        # Sonuçları düzleştir
        final_results = []
        for group in results_groups:
            final_results.extend(group)

        return final_results
