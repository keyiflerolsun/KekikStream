# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult
from selectolax.parser import HTMLParser
import re, json

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

    def _get_nonce(self, nonce_type: str = "video_nonce", referer: str = None) -> str:
        """Site cache'lenmiş nonce'ları expire olabiliyor, fresh nonce al"""
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
            nonces = resp.json().get("data", {}).get("nonces", {})
            return nonces.get(nonce_type, "")
        except:
            return ""

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = self.cloudscraper.get(url)
        secici = HTMLParser(istek.text)

        results = []
        for item in secici.css("div.items article"):
            title_el = item.css_first("h2")
            link_el  = item.css_first("a")
            img_el   = item.css_first("img")

            title  = title_el.text(strip=True) if title_el else None
            href   = link_el.attrs.get("href") if link_el else None
            poster = img_el.attrs.get("data-src") if img_el else None

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

        secici  = HTMLParser(html)
        results = []

        for item in secici.css("div.items article"):
            title_el = item.css_first("h2")
            link_el  = item.css_first("a")
            img_el   = item.css_first("img")

            title  = title_el.text(strip=True) if title_el else None
            href   = link_el.attrs.get("href") if link_el else None
            poster = img_el.attrs.get("data-src") if img_el else None

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster) if poster else None
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)
        html_text = istek.text

        title_el = secici.css_first("h1") or secici.css_first(".titles h1")
        raw_title = title_el.text(strip=True) if title_el else ""
        if not raw_title:
             # Alternatif title yeri
             title_meta = secici.css_first("meta[property='og:title']")
             raw_title = title_meta.attrs.get("content", "") if title_meta else ""
        
        title = re.sub(r"\s*izle.*$", "", raw_title, flags=re.IGNORECASE).strip()

        poster_el = secici.css_first("div.poster img")
        poster    = poster_el.attrs.get("src") if poster_el else None

        desc_el     = secici.css_first("div.wp-content p")
        description = desc_el.text(strip=True) if desc_el else None

        year_el = secici.css_first("div.extra span.C a")
        year = None
        if year_el:
            year_text = year_el.text(strip=True)
            year_match = re.search(r"\d{4}", year_text)
            year = year_match.group() if year_match else None

        tags = [a.text(strip=True) for a in secici.css("div.sgeneros a") if a.text(strip=True)]

        duration_el = secici.css_first("span.runtime")
        duration = None
        if duration_el:
            duration_text = duration_el.text(strip=True)
            dur_match = re.search(r"\d+", duration_text)
            duration = int(dur_match.group()) if dur_match else None

        actors = [span.text(strip=True) for span in secici.css("span.valor a > span") if span.text(strip=True)]

        trailer_match = re.search(r'embed/([^?]*)\?rel', html_text)
        trailer = f"https://www.youtube.com/embed/{trailer_match.group(1)}" if trailer_match else None

        # Dizi mi film mi kontrol et
        is_series = "/dizi/" in url

        if is_series:
            year_link_el = secici.css_first("a[href*='/yil/']")
            if year_link_el:
                year_elem = year_link_el.text(strip=True)
                year_match = re.search(r"\d{4}", year_elem)
                year = year_match.group() if year_match else year

            # Duration from info section
            for span in secici.css("div#info span"):
                span_text = span.text(strip=True) if span.text() else ""
                if "Dakika" in span_text:
                    dur_match = re.search(r"\d+", span_text)
                    duration = int(dur_match.group()) if dur_match else duration
                    break

            episodes = []
            for ep_item in secici.css("div#episodes ul.episodios li"):
                ep_title_el = ep_item.css_first("h4.episodiotitle a")
                ep_href = ep_title_el.attrs.get("href") if ep_title_el else None
                ep_name = ep_title_el.text(strip=True) if ep_title_el else None

                if not ep_href or not ep_name:
                    continue

                ep_detail = ep_name
                season_match = re.search(r"(\d+)\.\s*Sezon", ep_detail)
                episode_match = re.search(r"Sezon\s+(\d+)\.\s*Bölüm", ep_detail)

                ep_season = int(season_match.group(1)) if season_match else 1
                ep_episode = int(episode_match.group(1)) if episode_match else None

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
            year        = year,
            duration    = duration,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)

        nonce = self._get_nonce("video_nonce", referer=url)

        # partKey to dil label mapping
        part_key_labels = {
            "turkcedublaj"  : "Türkçe Dublaj",
            "turkcealtyazi" : "Türkçe Altyazı",
            "orijinal"      : "Orijinal"
        }

        links = []
        for player in secici.css("nav.player a"):
            source_id   = player.attrs.get("data-post-id")
            player_name = player.attrs.get("data-player-name")
            part_key    = player.attrs.get("data-part-key")

            if not source_id or "event" in source_id or source_id == "":
                continue

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
                continue

            iframe_url = data.get("data", {}).get("url")
            if not iframe_url:
                continue

            # SetPlay URL'si için part_key ekleme
            if "setplay" not in iframe_url and part_key:
                iframe_url = f"{iframe_url}?partKey={part_key}"

            # Dil etiketi oluştur
            label = part_key_labels.get(part_key, "")
            if not label and part_key:
                label = part_key.replace("_", " ").title()

            data = await self.extract(iframe_url, prefix=label if label else None)
            if data:
                links.append(data)

        return links
