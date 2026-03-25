# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper
from contextlib       import suppress

class FilmBip(PluginBase):
    name        = "FilmBip"
    language    = "tr"
    main_url    = "https://filmbip.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "FilmBip adlı film sitemizde Full HD film izle. Yerli ve yabancı filmleri Türkçe dublaj veya altyazılı şekilde 1080p yüksek kalite film izle"

    main_page   = {
        f"{main_url}/filmler/SAYFA"              : "Yeni Filmler",
        f"{main_url}/film/tur/aile/SAYFA"        : "Aile",
        f"{main_url}/film/tur/aksiyon/SAYFA"     : "Aksiyon",
        f"{main_url}/film/tur/belgesel/SAYFA"    : "Belgesel",
        f"{main_url}/film/tur/bilim-kurgu/SAYFA" : "Bilim Kurgu",
        f"{main_url}/film/tur/dram/SAYFA"        : "Dram",
        f"{main_url}/film/tur/fantastik/SAYFA"   : "Fantastik",
        f"{main_url}/film/tur/gerilim/SAYFA"     : "Gerilim",
        f"{main_url}/film/tur/gizem/SAYFA"       : "Gizem",
        f"{main_url}/film/tur/komedi/SAYFA"      : "Komedi",
        f"{main_url}/film/tur/korku/SAYFA"       : "Korku",
        f"{main_url}/film/tur/macera/SAYFA"      : "Macera",
        f"{main_url}/film/tur/muzik/SAYFA"       : "Müzik",
        f"{main_url}/film/tur/romantik/SAYFA"    : "Romantik",
        f"{main_url}/film/tur/savas/SAYFA"       : "Savaş",
        f"{main_url}/film/tur/suc/SAYFA"         : "Suç",
        f"{main_url}/film/tur/tarih/SAYFA"       : "Tarih",
        f"{main_url}/film/tur/vahsi-bati/SAYFA"  : "Western",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        page_url = url.replace("SAYFA", "") if page == 1 else url.replace("SAYFA", str(page))
        page_url = page_url.rstrip("/")

        istek  = await self.httpx.get(page_url)
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.poster-long"):
            title  = veri.select_attr("a.block img.lazy", "alt")
            href   = veri.select_attr("a.block", "href")
            poster = veri.select_poster("a.block img.lazy")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek = await self.httpx.post(
            url     = f"{self.main_url}/search",
            headers = {
                "Accept"           : "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With" : "XMLHttpRequest",
                "Content-Type"     : "application/x-www-form-urlencoded; charset=UTF-8",
                "Origin"           : self.main_url,
                "Referer"          : f"{self.main_url}/"
            },
            data    = {"query": query}
        )

        try:
            json_data = istek.json()
            if not json_data.get("success"):
                return []

            html_content = json_data.get("theme", "")
        except Exception:
            return []

        secici = HTMLHelper(html_content)

        results = []
        for veri in secici.select("li"):
            title  = veri.select_text("a.block.truncate")
            href   = veri.select_attr("a", "href")
            poster = veri.select_attr("img.lazy", "data-src")

            if title and href:
                results.append(SearchResult(
                    title  = title.strip(),
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_direct_text("div.page-title h1")
        poster      = secici.select_poster("div.series-profile-image a img")
        description = secici.select_text("div.series-profile-infos-in.article p") or secici.select_text("div.series-profile-summary p")
        tags        = secici.select_texts("div.series-profile-type.tv-show-profile-type a")
        year        = secici.extract_year("div.series-profile-infos-in") or secici.regex_first(r"\((\d{4})\)", title)
        duration    = secici.regex_first(r"(\d+)", secici.meta_value("Süre", container_selector="div.series-profile-infos"))
        rating      = secici.meta_value("IMDB Puanı", container_selector="div.series-profile-infos")
        rating      = rating.split("(")[0] if rating else None
        actors      = secici.select_attrs("div.series-profile-cast ul li a img", "alt")

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            year        = year,
            rating      = rating,
            duration    = duration,
            actors      = actors,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        extract_args = []
        for tab in secici.select("ul.tab.alternative-group li[data-number]"):
            tab_id   = tab.attrs.get("data-number")
            tab_name = tab.select_text(None)
            tab_hash = tab.attrs.get("data-group-hash")

            if not tab_id:
                continue

            button_data = [] # (player_name, iframe_url)

            # İlgili content divini bul
            content_div = secici.select_first(f"div#{tab_id}")

            # Eğer div var ve içi doluysa oradan al
            if content_div and content_div.select("ul li button"):
                buttons = content_div.select("ul li button")
                for btn in buttons:
                    button_data.append((btn.text(strip=True), btn.attrs.get("data-hhs")))

            elif tab_hash:
                # Div yok veya boş, AJAX ile çek
                with suppress(Exception):
                    hash_resp = await self.httpx.post(
                        url       = f"{self.main_url}/get/video/group",
                        headers   = {
                            "X-Requested-With" : "XMLHttpRequest",
                            "Content-Type"     : "application/x-www-form-urlencoded; charset=UTF-8",
                            "Referer"          : url
                        },
                        data    = {"hash": tab_hash}
                    )

                    if hash_resp.status_code == 200:
                        json_data = hash_resp.json()
                        if json_data.get("success"):
                            # 1. Videos listesi (API yanıtı)
                            if videos := json_data.get("videos"):
                                for vid in videos:
                                    button_data.append((vid.get("name"), vid.get("link")))

                            # 2. HTML content (Fallback)
                            else:
                                html_content = json_data.get("content") or json_data.get("html") or json_data.get("theme")
                                if html_content:
                                    sub_helper = HTMLHelper(html_content)
                                    sub_btns   = sub_helper.select("ul li button")
                                    for btn in sub_btns:
                                        button_data.append((btn.text(strip=True), btn.attrs.get("data-hhs")))

            for player_name, iframe_url in button_data:
                if iframe_url:
                    extract_args.append((self.fix_url(iframe_url), f"{tab_name} | {player_name}"))

        tasks   = [self.extract(url=url, name_override=name) for url, name in extract_args]
        results = []
        for data in await self.gather_with_limit(tasks):
            self.collect_results(results, data)

        if not results:
            trailer_id = secici.select_attr(".seriesFragmans", "data-yt") or secici.regex_first(r'data-yt="([^"]+)"')
            if trailer_id:
                results.append(ExtractResult(
                    name    = "Fragman",
                    url     = f"https://www.youtube.com/embed/{trailer_id}",
                    referer = url,
                ))

        # Eğer hiç sonuç bulunamazsa fallback
        if not results:
            fallback_iframes = []
            for player in secici.select("div#tv-spoox2"):
                if iframe := player.select_attr("iframe", "src"):
                    fallback_iframes.append(self.fix_url(iframe))

            tasks = [self.extract(iframe) for iframe in fallback_iframes]
            for data in await self.gather_with_limit(tasks):
                self.collect_results(results, data)

        return results
