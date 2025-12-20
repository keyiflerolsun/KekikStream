# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode
from parsel           import Selector
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

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = self.cloudscraper.get(url)
        secici = Selector(istek.text)

        results = []
        for item in secici.css("div.items article"):
            title  = item.css("h2::text").get()
            href   = item.css("a::attr(href)").get()
            poster = item.css("img::attr(data-src)").get()

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title.strip(),
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster) if poster else None
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        # Ana sayfadan nonce değerini al
        main_resp = self.cloudscraper.get(self.main_url)

        # Birden fazla nonce pattern dene
        nonce = ""
        nonce_patterns = [
            r'nonces:\s*\{\s*search:\s*"([^"]+)"',      # STMOVIE_AJAX.nonces.search
            r'"search":\s*"([a-zA-Z0-9]+)"',            # JSON format
            r"nonce:\s*'([^']*)'",
            r'"nonce":"([^"]+)"',
            r'data-nonce="([^"]+)"',
        ]
        for pattern in nonce_patterns:
            match = re.search(pattern, main_resp.text)
            if match:
                nonce = match.group(1)
                break

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

        secici  = Selector(text=html)
        results = []

        for item in secici.css("div.items article"):
            title  = item.css("h2::text").get()
            href   = item.css("a::attr(href)").get()
            poster = item.css("img::attr(data-src)").get()

            if title and href:
                results.append(SearchResult(
                    title  = title.strip(),
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster) if poster else None
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        raw_title   = secici.css("h1::text").get() or ""
        title       = re.sub(r"\s*izle.*$", "", raw_title, flags=re.IGNORECASE).strip()
        poster      = secici.css("div.poster img::attr(src)").get()
        description = secici.css("div.wp-content p::text").get()
        year        = secici.css("div.extra span.C a::text").get()
        if year:
            year_match = re.search(r"\d{4}", year)
            year = year_match.group() if year_match else None
        tags     = [a.css("::text").get().strip() for a in secici.css("div.sgeneros a") if a.css("::text").get()]
        duration = secici.css("span.runtime::text").get()
        if duration:
            dur_match = re.search(r"\d+", duration)
            duration = int(dur_match.group()) if dur_match else None

        actors = [span.css("::text").get().strip() for span in secici.css("span.valor a > span") if span.css("::text").get()]

        trailer_match = re.search(r'embed/([^?]*)\?rel', istek.text)
        trailer = f"https://www.youtube.com/embed/{trailer_match.group(1)}" if trailer_match else None

        # Dizi mi film mi kontrol et
        is_series = "/dizi/" in url

        if is_series:
            year_elem = secici.css("a[href*='/yil/']::text").get()
            if year_elem:
                year_match = re.search(r"\d{4}", year_elem)
                year = year_match.group() if year_match else year

            dur_elem = secici.css("div#info span:contains('Dakika')::text").get()
            if dur_elem:
                dur_match = re.search(r"\d+", dur_elem)
                duration = int(dur_match.group()) if dur_match else duration

            episodes = []
            for ep_item in secici.css("div#episodes ul.episodios li"):
                ep_href = ep_item.css("h4.episodiotitle a::attr(href)").get()
                ep_name = ep_item.css("h4.episodiotitle a::text").get()

                if not ep_href or not ep_name:
                    continue

                ep_detail = ep_name.strip()
                season_match = re.search(r"(\d+)\.\s*Sezon", ep_detail)
                episode_match = re.search(r"Sezon\s+(\d+)\.\s*Bölüm", ep_detail)

                ep_season = int(season_match.group(1)) if season_match else 1
                ep_episode = int(episode_match.group(1)) if episode_match else None

                episodes.append(Episode(
                    season  = ep_season,
                    episode = ep_episode,
                    title   = ep_name.strip(),
                    url     = self.fix_url(ep_href)
                ))

            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster) if poster else None,
                title       = title,
                description = description.strip() if description else None,
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
            description = description.strip() if description else None,
            tags        = tags,
            year        = year,
            duration    = duration,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[dict]:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        nonce = secici.css("div#playex::attr(data-nonce)").get() or ""

        # partKey to dil label mapping
        part_key_labels = {
            "turkcedublaj"  : "Türkçe Dublaj",
            "turkcealtyazi" : "Türkçe Altyazı",
            "orijinal"      : "Orijinal"
        }

        links = []
        for player in secici.css("nav.player a"):
            source_id   = player.css("::attr(data-post-id)").get()
            player_name = player.css("::attr(data-player-name)").get()
            part_key    = player.css("::attr(data-part-key)").get()

            if not source_id or "event" in source_id or source_id == "":
                continue

            # Multipart form request
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

            extractor = self.ex_manager.find_extractor(iframe_url)
            name = extractor.name if extractor else player_name or "Direct Link"
            if label:
                name = f"{name} | {label}"

            links.append({
                "url"     : iframe_url,
                "name"    : name,
                "referer" : self.main_url
            })

        return links
