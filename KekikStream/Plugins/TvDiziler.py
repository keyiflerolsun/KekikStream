# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
from unicodedata      import normalize
import re

class TvDiziler(PluginBase):
    name        = "TvDiziler"
    language    = "tr"
    main_url    = "https://tvdiziler.tv"
    favicon     = f"https://www.google.com/s2/favicons?domain=tvdiziler.tv&sz=64"
    description = "Ücretsiz yerli dizi izleme sitesi en popüler tv diziler tek parça hd kalitesiyle ve reklamsız olarak son bölüm tv dizileri izleyin."

    main_page   = {
        f"{main_url}"                              : "Son Bölümler",
        f"{main_url}/dizi/tur/aile"                : "Aile",
        f"{main_url}/dizi/tur/aksiyon"             : "Aksiyon",
        f"{main_url}/dizi/tur/aksiyon-macera"      : "Aksiyon-Macera",
        f"{main_url}/dizi/tur/bilim-kurgu-fantazi" : "Bilim Kurgu & Fantazi",
        f"{main_url}/dizi/tur/fantastik"           : "Fantastik",
        f"{main_url}/dizi/tur/gerilim"             : "Gerilim",
        f"{main_url}/dizi/tur/gizem"               : "Gizem",
        f"{main_url}/dizi/tur/komedi"              : "Komedi",
        f"{main_url}/dizi/tur/korku"               : "Korku",
        f"{main_url}/dizi/tur/macera"              : "Macera",
        f"{main_url}/dizi/tur/pembe-dizi"          : "Pembe Dizi",
        f"{main_url}/dizi/tur/romantik"            : "Romantik",
        f"{main_url}/dizi/tur/savas"               : "Savaş",
        f"{main_url}/dizi/tur/suc"                 : "Suç",
        f"{main_url}/dizi/tur/tarih"               : "Tarih",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        if category == "Son Bölümler":
            istek  = await self.httpx.get(url)
            secici = HTMLHelper(istek.text)

            results = []
            for veri in secici.select("div.poster-xs"):
                title  = veri.select_text("div.poster-xs-subject h2")
                href   = veri.select_attr("a", "href")
                poster = veri.select_attr("div.poster-xs-image img", "data-src")

                if title and href:
                    results.append(MainPageResult(
                        category = category,
                        title    = title.replace(" izle", ""),
                        url      = self.fix_url(href),
                        poster   = self.fix_url(poster),
                    ))

            return results

        istek  = await self.httpx.get(f"{url}/{page}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.poster-long"):
            title  = veri.select_text("div.poster-long-subject h2")
            href   = veri.select_attr("div.poster-long-subject a", "href")
            poster = veri.select_attr("div.poster-long-image img", "data-src")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title.replace(" izle", ""),
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        headers = {
            "X-Requested-With" : "XMLHttpRequest",
            "Accept"           : "application/json, text/javascript, */*; q=0.01",
        }
        istek = await self.httpx.post(f"{self.main_url}/search?qr={query}", headers=headers)

        results = []
        try:
            data         = istek.json()
            html_content = ""
            if isinstance(data, dict):
                html_content = data.get("data") or data.get("theme") or data.get("html") or ""
            elif isinstance(data, list):
                html_content = "".join(item for item in data if isinstance(item, str))

            secici = HTMLHelper(html_content) if html_content else HTMLHelper(istek.text)

            for item in secici.select("li.col, li[class*='col'], a.search-result-item"):
                href   = item.select_attr("a", "href") or item.select_attr(None, "href")
                title  = item.select_text("h3") or item.select_text("span.title") or item.select_attr("img", "alt") or item.text(strip=True)
                poster = item.select_attr("img", "data-src") or item.select_attr("img", "src")

                if title and href:
                    results.append(SearchResult(
                        title  = title.strip().replace(" izle", ""),
                        url    = self.fix_url(href),
                        poster = self.fix_url(poster),
                    ))
        except Exception:
            # Fallback to direct search if AJAX fails
            pass

        if results:
            return self._dedupe_search_results(results)

        query_norm = self._normalize_search_text(query)
        for index, (page_url, category) in enumerate(self.main_page.items()):
            if index >= 6:
                break

            for item in await self.get_main_page(1, page_url, category):
                if query_norm not in self._normalize_search_text(item.title) and query_norm not in self._normalize_search_text(item.url):
                    continue

                results.append(SearchResult(
                    title  = item.title,
                    url    = item.url,
                    poster = item.poster,
                ))

        return self._dedupe_search_results(results)

    @staticmethod
    def _normalize_search_text(text: str) -> str:
        return normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()

    @staticmethod
    def _dedupe_search_results(results: list[SearchResult]) -> list[SearchResult]:
        deduped = []
        seen    = set()

        for item in results:
            if not item.url or item.url in seen:
                continue
            seen.add(item.url)
            deduped.append(item)

        return deduped

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url, headers={"Referer": f"{self.main_url}/"})
        secici = HTMLHelper(istek.text)

        # Bölüm sayfasıysa, breadcrumb'dan dizi sayfasına yönlendir
        if "/dizi/" not in url:
            for link in secici.select("div.breadcrumb a"):
                href = link.select_attr(None, "href")
                if href and "dizi/" in href and "/tur/" not in href:
                    return await self.load_item(self.fix_url(href))

        title       = secici.select_text("div.page-title p") or secici.select_text("div.page-title h1")
        title       = (title or "").replace(" izle", "")
        poster      = secici.select_attr("div.series-profile-image img", "data-src")
        year        = secici.regex_first(r"\((\d{4})\)", secici.select_text("h1 span"))
        description = secici.select_text("div.series-profile-summary p")
        tags        = secici.select_texts("div.series-profile-type a")

        actors = []
        for cast in secici.select("div.series-profile-cast li"):
            name = cast.select_text("h5.truncate")
            if name:
                actors.append(name.strip())

        episodes = []
        szn      = 1
        for sezon in secici.select("div.series-profile-episode-list"):
            blm = 1
            for bolum in sezon.select("li"):
                ep_name = bolum.select_text("h6.truncate a")
                ep_href = bolum.select_attr("h6.truncate a", "href")
                if not ep_name or not ep_href:
                    continue

                episodes.append(Episode(
                    season  = szn,
                    episode = blm,
                    title   = ep_name,
                    url     = self.fix_url(ep_href),
                ))
                blm += 1
            szn += 1

        # Eğer bölüm listesi boşsa ve doğrudan bir bölüm URL'siyse
        if not episodes:
            episodes.append(Episode(
                season  = 1,
                episode = 1,
                title   = title,
                url     = url,
            ))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            year        = year,
            actors      = actors,
            episodes    = episodes,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        headers = {"Referer": f"{self.main_url}/"}
        istek   = await self.httpx.get(url, headers=headers)
        secici  = HTMLHelper(istek.text)

        response  = []
        seen_srcs = set()

        # Altyazılı / Dublaj gruplarını bul
        panes = secici.select("div.tab-pane, div.series-watch-alternatives")
        if panes:
            for group in panes:
                group_id = group.id if hasattr(group, "id") and isinstance(group.id, str) else ""
                prefix   = "Altyazı" if "altyazi" in group_id else "Dublaj" if "dublaj" in group_id else ""

                for btn in group.select("button[data-hhs]"):
                    data_hhs_raw = btn.select_attr(None, "data-hhs")
                    if not data_hhs_raw: continue
                    for src in data_hhs_raw.split(","):
                        if not src or "404.html" in src or src in seen_srcs:
                            continue
                        seen_srcs.add(src)

                        name       = btn.text(strip=True) or "Player"
                        player_url = self.fix_url(src)

                        if "/vid/kapat/?git=" in player_url:
                            player_url = player_url.split("git=")[-1]

                        full_name = f"{prefix} | {name}" if prefix else name

                        if "/vid/ply/" in player_url:
                            data = await self._extract_internal_player(player_url, prefix=full_name)
                            self.collect_results(response, data)
                        else:
                            data = await self.extract(player_url, referer=url, prefix=full_name)
                            self.collect_results(response, data)
        else:
            for btn in secici.select("button[data-hhs]"):
                data_hhs_raw = btn.select_attr(None, "data-hhs")
                if not data_hhs_raw: continue
                for src in data_hhs_raw.split(","):
                    if not src or "404.html" in src or src in seen_srcs:
                        continue
                    seen_srcs.add(src)

                    name       = btn.text(strip=True) or "Player"
                    player_url = self.fix_url(src)

                    if "/vid/kapat/?git=" in player_url:
                        player_url = player_url.split("git=")[-1]

                    if "/vid/ply/" in player_url:
                        data = await self._extract_internal_player(player_url, prefix=name)
                        self.collect_results(response, data)
                    else:
                        data = await self.extract(player_url, referer=url, prefix=name)
                        self.collect_results(response, data)

        # 2. Iframe'den topla
        for iframe in secici.select("iframe"):
            iframe_src = iframe.attrs.get("src")
            if iframe_src and "404.html" not in iframe_src:
                iframe_url = self.fix_url(iframe_src)
                if iframe_url not in seen_srcs and "youtube.com" not in iframe_url:
                    seen_srcs.add(iframe_url)
                    if "/vid/ply/" in iframe_url:
                        data = await self._extract_internal_player(iframe_url)
                    else:
                        data = await self.extract(iframe_url, referer=url)
                    self.collect_results(response, data)

        return self.deduplicate(response)

    async def _extract_internal_player(self, url, prefix="") -> list[ExtractResult]:
        """TvDiziler internal player extractor (tvdiziler.tv/vid/ply/)"""
        try:
            headers = {"Referer": f"{self.main_url}/"}
            istek   = await self.httpx.get(url, headers=headers)

            # JWPlayer setup find sources
            match = re.search(r'sources:\s*(\[.*?\])', istek.text, re.DOTALL)
            if not match:
                return []

            sources_str = match.group(1)
            results     = []
            for block_match in re.finditer(r'\{(.*?)\}', sources_str):
                block   = block_match.group(1)
                file_m  = re.search(r'file\s*:\s*[\'\"]([^\'\"]+)[\'\"]', block)
                label_m = re.search(r'label\s*:\s*[\'\"]([^\'\"]+)[\'\"]', block)

                if file_m:
                    file_url = file_m.group(1)
                    raw_lbl  = label_m.group(1) if label_m else ""
                    label    = raw_lbl or prefix or "Internal"

                    results.append(ExtractResult(
                        name = f"{prefix} | {label}" if prefix and raw_lbl else label,
                        url  = file_url
                    ))
            return results
        except Exception:
            return []
