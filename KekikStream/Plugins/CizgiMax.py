# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper

class CizgiMax(PluginBase):
    name        = "CizgiMax"
    language    = "tr"
    main_url    = "https://cizgimax.online"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "ÇizgiMax ile Çizgi Film izlemek artık daha kolay, donmadan full hd ve reklamsız bir sitedir, içerisinde 500 den fazla çizgi film olan, Bu site bu işi profesyonelce yapıyor."

    main_page   = {
        f"{main_url}/diziler?orderby=date&order=DESC"                                   : "Son Eklenenler",
        f"{main_url}/diziler?s_type&tur[0]=aile&orderby=date&order=DESC"                : "Aile",
        f"{main_url}/diziler?s_type&tur[0]=aksiyon-macera&orderby=date&order=DESC"      : "Aksiyon & Macera",
        f"{main_url}/diziler?s_type&tur[0]=animasyon&orderby=date&order=DESC"           : "Animasyon",
        f"{main_url}/diziler?s_type&tur[0]=belgesel&orderby=date&order=DESC"            : "Belgesel",
        f"{main_url}/diziler?s_type&tur[0]=bilim-kurgu-fantazi&orderby=date&order=DESC" : "Bilim Kurgu & Fantazi",
        f"{main_url}/diziler?s_type&tur[0]=cocuklar&orderby=date&order=DESC"            : "Çocuklar",
        f"{main_url}/diziler?s_type&tur[0]=dram&orderby=date&order=DESC"                : "Dram",
        f"{main_url}/diziler?s_type&tur[0]=gizem&orderby=date&order=DESC"               : "Gizem",
        f"{main_url}/diziler?s_type&tur[0]=komedi&orderby=date&order=DESC"              : "Komedi",
        f"{main_url}/diziler?s_type&tur[0]=pembe-dizi&orderby=date&order=DESC"          : "Pembe Dizi",
        f"{main_url}/diziler?s_type&tur[0]=suc&orderby=date&order=DESC"                 : "Suç",
        f"{main_url}/diziler?s_type&tur[0]=talk&orderby=date&order=DESC"                : "Talk",
        f"{main_url}/diziler?s_type&tur[0]=vahsi-bati&orderby=date&order=DESC"          : "Vahşi Batı",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        sep      = "&" if "?" in url else "?"
        page_url = f"{self.main_url}/diziler/page/{page}" + url.split("/diziler")[1] if "/diziler" in url else url
        istek    = await self.httpx.get(page_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("ul.filter-results li"):
            title  = veri.select_text("h2.truncate")
            href   = veri.select_attr("div.poster-subject a", "href")
            poster = veri.select_attr("div.poster-media img", "data-src")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title.strip(),
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        resp = await self.httpx.get(f"{self.main_url}/ajaxservice/index.php?qr={query}")

        results = []
        try:
            data  = resp.json()
            items = data.get("data", {}).get("result", [])
        except Exception:
            return results

        for item in items:
            s_name = item.get("s_name", "")
            s_link = item.get("s_link", "")
            s_img  = item.get("s_image")

            # Bölüm/Sezon sonuçlarını filtrele
            if any(kw in s_name for kw in [".Bölüm", ".Sezon", "-Sezon", "-izle"]):
                continue

            if s_name and s_link:
                results.append(SearchResult(
                    title  = s_name.strip(),
                    url    = self.fix_url(s_link),
                    poster = self.fix_url(s_img),
                ))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("h1.page-title") or ""
        poster      = secici.select_attr("img.series-profile-thumb", "src")
        description = secici.select_text("#tv-series-desc") or secici.select_attr("meta[property='og:description']", "content")
        tags        = secici.select_texts("div.genre-item a")

        episodes = []
        for veri in secici.select("div.asisotope div.ajax_post"):
            ep_name  = veri.select_text("span.episode-names")
            ep_href  = veri.select_attr("a", "href")
            szn_name = veri.select_text("span.season-name") or ""

            if not ep_name or not ep_href:
                continue

            ep_season, ep_num = secici.extract_season_episode(f"{szn_name} {ep_name}")
            ep_season = ep_season or 1

            episodes.append(Episode(
                season  = ep_season,
                episode = ep_num,
                title   = ep_name.strip(),
                url     = self.fix_url(ep_href),
            ))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title.strip(),
            description = description,
            tags        = tags,
            episodes    = episodes,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        iframes = []
        for li in secici.select("ul.linkler li"):
            iframe = li.select_attr("a", "data-frame")
            if iframe:
                iframes.append(self.fix_url(iframe.strip()))

        tasks    = [self.extract(url, referer=f"{self.main_url}/") for url in iframes]
        response = []
        for data in await self.gather_with_limit(tasks):
            self.collect_results(response, data)

        return self.deduplicate(response)
