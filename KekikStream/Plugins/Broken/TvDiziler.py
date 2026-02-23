# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re, json

class TvDiziler(PluginBase):
    name        = "TvDiziler"
    language    = "tr"
    main_url    = "https://tvdiziler.tv"
    favicon     = f"https://www.google.com/s2/favicons?domain=tvdiziler.tv&sz=64"
    description = "Ücretsiz yerli dizi izleme sitesi en popüler tv diziler tek parça hd kalitesiyle ve reklamsız olarak son bölüm tv dizileri izleyin."

    main_page   = {
        f"{main_url}"                                  : "Son Bölümler",
        f"{main_url}/dizi/tur/aile"                    : "Aile",
        f"{main_url}/dizi/tur/aksiyon"                 : "Aksiyon",
        f"{main_url}/dizi/tur/aksiyon-macera"          : "Aksiyon-Macera",
        f"{main_url}/dizi/tur/bilim-kurgu-fantazi"     : "Bilim Kurgu & Fantazi",
        f"{main_url}/dizi/tur/fantastik"               : "Fantastik",
        f"{main_url}/dizi/tur/gerilim"                 : "Gerilim",
        f"{main_url}/dizi/tur/gizem"                   : "Gizem",
        f"{main_url}/dizi/tur/komedi"                  : "Komedi",
        f"{main_url}/dizi/tur/korku"                   : "Korku",
        f"{main_url}/dizi/tur/macera"                  : "Macera",
        f"{main_url}/dizi/tur/pembe-dizi"              : "Pembe Dizi",
        f"{main_url}/dizi/tur/romantik"                : "Romantik",
        f"{main_url}/dizi/tur/savas"                   : "Savaş",
        f"{main_url}/dizi/tur/suc"                     : "Suç",
        f"{main_url}/dizi/tur/tarih"                   : "Tarih",
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
        istek = await self.httpx.post(
            f"{self.main_url}/search?qr={query}",
            headers = {
                "X-Requested-With" : "XMLHttpRequest",
                "Accept"           : "application/json, text/javascript, */*; q=0.01",
            },
        )

        results = []
        try:
            data = istek.json()
            if data.get("success") != 1:
                return results

            html   = data.get("data", "")
            secici = HTMLHelper(html)

            for li in secici.select("ul li"):
                href = li.select_attr("a", "href")
                if not href or ("/dizi/" not in href and "/film/" not in href):
                    continue

                title  = li.select_text("h3.truncate")
                poster = li.select_attr("img", "data-src")

                if title and href:
                    results.append(SearchResult(
                        title  = title.strip().replace(" izle", ""),
                        url    = self.fix_url(href),
                        poster = self.fix_url(poster),
                    ))
        except Exception:
            pass

        return results

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

        response = []

        # Tüm butonlardan data-hhs topla (aktif + alternatifler)
        seen_srcs = set()
        src_list  = []
        for btn in secici.select("button[data-hhs]"):
            src = btn.select_attr(None, "data-hhs")
            if not src or src in seen_srcs:
                continue
            seen_srcs.add(src)
            src = self.fix_url(src)
            if "youtube.com" in src:
                continue
            src_list.append(src)

        async def _process_src(src):
            part_results = []
            try:
                if_resp = await self.httpx.get(src, headers=headers)
                script_match = re.search(r"sources:\s*\[(\{[^]]+)\]", if_resp.text)
                if script_match:
                    raw = script_match.group(1)
                    raw = re.sub(r'(?<!["\w])(\w+)(?=\s*:)', r'"\1"', raw)
                    raw = raw.replace("'", '"')
                    try:
                        source   = json.loads(raw)
                        file_url = source.get("file", "")
                        if file_url:
                            part_results.append(ExtractResult(
                                name    = self.name,
                                url     = file_url,
                                referer = f"{self.main_url}/",
                            ))
                    except json.JSONDecodeError:
                        pass
            except Exception:
                pass

            # Fallback: extractor
            data = await self.extract(src, referer=f"{self.main_url}/")
            self.collect_results(part_results, data)
            return part_results

        tasks = [_process_src(src) for src in src_list]
        for result_list in await self.gather_with_limit(tasks):
            response.extend(result_list)

        # Eğer hiç buton yoksa, eski fallback
        if not seen_srcs:
            iframe_src = secici.select_attr("iframe", "src")
            if iframe_src:
                iframe_src = self.fix_url(iframe_src)
                data       = await self.extract(iframe_src, referer=f"{self.main_url}/")
                self.collect_results(response, data)

        return self.deduplicate(response)
