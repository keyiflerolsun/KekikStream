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

        title       = self.clean_title(secici.select_text("h1") or secici.select_text(".titles h1") or secici.select_attr("meta[property='og:title']", "content"))
        poster      = secici.select_poster("div.poster img")
        description = secici.select_text("div.wp-content p")
        rating      = secici.select_text("b#repimdb strong") or secici.regex_first(r"([\d.]+)", secici.select_text("div.imdb"))
        year        = secici.extract_year("div.extra span.valor")
        tags        = secici.select_texts("div.sgeneros a")
        duration    = int(secici.regex_first(r"(\d+)", secici.select_text("span.runtime")) or 0)
        actors      = secici.select_texts("span.valor a[href*='/oyuncu/']")

        common_info = {
            "url"         : url,
            "poster"      : self.fix_url(poster) if poster else None,
            "title"       : title or "Bilinmiyor",
            "description" : description,
            "tags"        : tags,
            "rating"      : rating,
            "year"        : str(year) if year else None,
            "duration"    : duration,
            "actors"      : actors
        }

        if "/dizi/" in url:
            episodes = []
            for ep_item in secici.select("div#episodes ul.episodios li"):
                href = secici.select_attr("h4.episodiotitle a", "href", ep_item)
                name = secici.select_text("h4.episodiotitle a", ep_item)
                if href and name:
                    s, e = secici.extract_season_episode(name)
                    episodes.append(Episode(season=s or 1, episode=e or 1, title=name, url=self.fix_url(href)))
            return SeriesInfo(**common_info, episodes=episodes)

        return MovieInfo(**common_info)

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
