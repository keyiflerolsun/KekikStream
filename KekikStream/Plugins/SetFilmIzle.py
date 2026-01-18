# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
import json, asyncio

class SetFilmIzle(PluginBase):
    name        = "SetFilmIzle"
    language    = "tr"
    main_url    = "https://www.setfilmizle.uk"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Setfilmizle sitemizde, donma yaşamadan Türkçe dublaj ve altyazılı filmleri ile dizileri muhteşem 1080p full HD kalitesinde izleyebilirsiniz."

    main_page   = {
        f"{main_url}/tur/aile/"        : "Aile",
        f"{main_url}/tur/aksiyon/"     : "Aksiyon",
        f"{main_url}/tur/animasyon/"   : "Animasyon",
        f"{main_url}/tur/belgesel/"    : "Belgesel",
        f"{main_url}/tur/bilim-kurgu/" : "Bilim-Kurgu",
        f"{main_url}/tur/biyografi/"   : "Biyografi",
        f"{main_url}/tur/dini/"        : "Dini",
        f"{main_url}/tur/dram/"        : "Dram",
        f"{main_url}/tur/fantastik/"   : "Fantastik",
        f"{main_url}/tur/genclik/"     : "Gençlik",
        f"{main_url}/tur/gerilim/"     : "Gerilim",
        f"{main_url}/tur/gizem/"       : "Gizem",
        f"{main_url}/tur/komedi/"      : "Komedi",
        f"{main_url}/tur/korku/"       : "Korku",
        f"{main_url}/tur/macera/"      : "Macera",
        f"{main_url}/tur/romantik/"    : "Romantik",
        f"{main_url}/tur/savas/"       : "Savaş",
        f"{main_url}/tur/suc/"         : "Suç",
        f"{main_url}/tur/tarih/"       : "Tarih",
        f"{main_url}/tur/western/"     : "Western"
    }

    def _get_nonce(self, nonce_type: str = "video", referer: str = None) -> str:
        """Site cache'lenmiş nonce'ları expire olabiliyor, fresh nonce al veya sayfadan çek"""
        try:
            resp = self.cloudscraper.post(
                f"{self.main_url}/wp-admin/admin-ajax.php",
                headers = {
                    "Referer"      : referer or self.main_url,
                    "Origin"       : self.main_url,
                    "Content-Type" : "application/x-www-form-urlencoded",
                },
                data = "action=st_cache_refresh_nonces"
            )
            data = resp.json()
            if data and data.get("success"):
                nonces = data.get("data", {}).get("nonces", {})
                return nonces.get(nonce_type if nonce_type != "search" else "dt_ajax_search", "")
        except:
            pass

        # AJAX başarısızsa sayfadan çekmeyi dene
        try:
            main_resp = self.cloudscraper.get(referer or self.main_url)
            # STMOVIE_AJAX = { ... nonces: { search: "...", ... } }
            nonce = HTMLHelper(main_resp.text).regex_first(rf'"{nonce_type}":\s*"([^"]+)"')
            return nonce or ""
        except:
            return ""

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = self.cloudscraper.get(url)
        secici = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.items article"):
            title  = secici.select_text("h2", item)
            href   = secici.select_attr("a", "href", item)
            poster = secici.select_attr("img", "data-src", item)

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster) if poster else None
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        nonce = self._get_nonce("search")

        search_resp = self.cloudscraper.post(
            f"{self.main_url}/wp-admin/admin-ajax.php",
            headers = {
                "X-Requested-With" : "XMLHttpRequest",
                "Content-Type"     : "application/x-www-form-urlencoded",
                "Referer"          : f"{self.main_url}/"
            },
            data    = {
                "action"          : "ajax_search",
                "search"          : query,
                "original_search" : query,
                "nonce"           : nonce
            }
        )

        try:
            data = search_resp.json()
            html = data.get("html", "")
        except:
            return []

        secici  = HTMLHelper(html)
        results = []

        for item in secici.select("div.items article"):
            title  = secici.select_text("h2", item)
            href   = secici.select_attr("a", "href", item)
            poster = secici.select_attr("img", "data-src", item)

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster) if poster else None
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = self.cloudscraper.get(url)
        secici = HTMLHelper(istek.text)
        html_text = istek.text

        raw_title = secici.select_text("h1") or secici.select_text(".titles h1") or secici.select_attr("meta[property='og:title']", "content") or ""
        title = HTMLHelper(raw_title).regex_replace(r"(?i)\s*izle.*$", "", flags=0).strip()

        poster = secici.select_attr("div.poster img", "src")

        description = secici.select_text("div.wp-content p")

        rating = secici.select_text("b#repimdb strong") or secici.regex_first(r'repimdb"><strong>\s*([^<]+)</strong>', html_text)
        
        # Yıl için info bölümünden veya regex ile yakala
        year = secici.regex_first(r'(\d{4})', secici.select_text("div.extra span.valor") or secici.select_text("span.valor") or "")
        if not year:
            year = secici.regex_first(r'<span>(\d{4})</span>', html_text) or secici.regex_first(r'(\d{4})', html_text)

        tags = [a.text(strip=True) for a in secici.select("div.sgeneros a") if a.text(strip=True)]

        duration_text = secici.select_text("span.runtime")
        duration = int(secici.regex_first(r"\d+", duration_text)) if duration_text and secici.regex_first(r"\d+", duration_text) else None

        actors = [a.text(strip=True) for a in secici.select("span.valor a") if "/oyuncu/" in (a.attrs.get("href") or "")]
        if not actors:
             actors = secici.regex_all(r'href="[^"]*/oyuncu/[^"]*">([^<]+)</a>')

        trailer = None
        if trailer_id := secici.regex_first(r'embed/([^?]*)\?rel', html_text):
            trailer = f"https://www.youtube.com/embed/{trailer_id}"

        # Dizi mi film mi kontrol et
        is_series = "/dizi/" in url

        if is_series:
            year_elem = secici.select_text("a[href*='/yil/']")
            if year_elem:
                year = secici.regex_first(r"\d{4}", year_elem) or year

            # Duration from info section
            for span in secici.select("div#info span"):
                span_text = span.text(strip=True) if span.text() else ""
                if "Dakika" in span_text:
                    duration = secici.regex_first(r"\d+", span_text) and int(secici.regex_first(r"\d+", span_text))
                    break

            episodes = []
            for ep_item in secici.select("div#episodes ul.episodios li"):
                ep_href = secici.select_attr("h4.episodiotitle a", "href", ep_item)
                ep_name = secici.select_text("h4.episodiotitle a", ep_item)

                if not ep_href or not ep_name:
                    continue

                ep_detail = ep_name
                ep_season = secici.regex_first(r"(\d+)\.\s*Sezon", ep_detail) or 1
                ep_episode = secici.regex_first(r"Sezon\s+(\d+)\.\s*Bölüm", ep_detail)

                ep_season = int(ep_season) if isinstance(ep_season, str) and ep_season.isdigit() else 1
                ep_episode = int(ep_episode) if isinstance(ep_episode, str) and ep_episode.isdigit() else None

                episodes.append(Episode(
                    season  = ep_season,
                    episode = ep_episode,
                    title   = ep_name,
                    url     = self.fix_url(ep_href)
                ))
            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster) if poster else None,
                title       = title,
                description = description,
                tags        = tags,
                rating      = rating,
                year        = year,
                duration    = duration,
                actors      = actors,
                episodes    = episodes
            )

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster) if poster else None,
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            duration    = duration,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        nonce = secici.select_attr("div#playex", "data-nonce") or ""

        # partKey to dil label mapping
        part_key_labels = {
            "turkcedublaj"  : "Türkçe Dublaj",
            "turkcealtyazi" : "Türkçe Altyazı",
            "orijinal"      : "Orijinal"
        }

        semaphore = asyncio.Semaphore(5)
        tasks = []

        async def fetch_and_extract(player):
            async with semaphore:
                source_id   = player.attrs.get("data-post-id")
                player_name = player.attrs.get("data-player-name")
                part_key    = player.attrs.get("data-part-key")

                if not source_id or "event" in source_id or source_id == "":
                    return None

                try:
                    resp = self.cloudscraper.post(
                        f"{self.main_url}/wp-admin/admin-ajax.php",
                        headers = {"Referer": url},
                        data    = {
                            "action"      : "get_video_url",
                            "nonce"       : nonce,
                            "post_id"     : source_id,
                            "player_name" : player_name or "",
                            "part_key"    : part_key or ""
                        }
                    )
                    data = resp.json()
                except:
                    return None

                iframe_url = data.get("data", {}).get("url")
                if not iframe_url:
                    return None

                if "setplay" not in iframe_url and part_key:
                    iframe_url = f"{iframe_url}?partKey={part_key}"

                label = part_key_labels.get(part_key, "")
                if not label and part_key:
                    label = part_key.replace("_", " ").title()

                return await self.extract(iframe_url, prefix=label if label else None)

        for player in secici.select("nav.player a"):
            tasks.append(fetch_and_extract(player))

        results = await asyncio.gather(*tasks)
        return [r for r in results if r]
