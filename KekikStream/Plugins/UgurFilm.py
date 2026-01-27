# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper
import asyncio, contextlib

class UgurFilm(PluginBase):
    name        = "UgurFilm"
    language    = "tr"
    main_url    = "https://ugurfilm3.xyz"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Uğur Film ile film izle! En yeni ve güncel filmleri, Türk yerli filmleri Full HD 1080p kalitede Türkçe Altyazılı olarak izle."

    main_page   = {
        f"{main_url}/turkce-altyazili-filmler/page/" : "Türkçe Altyazılı Filmler",
        f"{main_url}/yerli-filmler/page/"            : "Yerli Filmler",
        f"{main_url}/en-cok-izlenen-filmler/page/"   : "En Çok İzlenen Filmler",
        f"{main_url}/category/kisa-film/page/"       : "Kısa Film",
        f"{main_url}/category/aksiyon/page/"         : "Aksiyon",
        f"{main_url}/category/bilim-kurgu/page/"     : "Bilim Kurgu",
        f"{main_url}/category/belgesel/page/"        : "Belgesel",
        f"{main_url}/category/komedi/page/"          : "Komedi",
        f"{main_url}/category/kara-film/page/"       : "Kara Film",
        f"{main_url}/category/erotik/page/"          : "Erotik"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}{page}", follow_redirects=True)
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.icerik div"):
            # Title is in the second span (a.baslik > span), not the first span (class="sol" which is empty)
            title = secici.select_text("a.baslik span", veri)
            if not title:
                continue

            href   = secici.select_attr("a", "href", veri)
            poster = secici.select_attr("img", "src", veri)

            results.append(MainPageResult(
                category = category,
                title    = title,
                url      = self.fix_url(href) if href else "",
                poster   = self.fix_url(poster),
            ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for film in secici.select("div.icerik div"):
            title  = secici.select_text("a.baslik span", film)
            href   = secici.select_attr("a", "href", film)
            poster = secici.select_attr("img", "src", film)

            if title and href:
                results.append(SearchResult(
                    title  = title.strip(),
                    url    = self.fix_url(href.strip()),
                    poster = self.fix_url(poster.strip()) if poster else None,
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("div.bilgi h2")
        poster      = secici.select_poster("div.resim img")
        description = secici.select_text("div.slayt-aciklama")
        rating      = secici.select_text("b#puandegistir")
        tags        = secici.select_texts("p.tur a[href*='/category/']")
        year        = secici.extract_year("a[href*='/yil/']")
        actors      = secici.select_texts("li.oyuncu-k span")
        duration    = secici.regex_first(r"(\d+) Dakika", secici.select_text("div.bilgi b"))

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            rating      = rating,
            tags        = tags,
            year        = year,
            actors      = actors,
            duration    = duration
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek   = await self.httpx.get(url)
        secici  = HTMLHelper(istek.text)
        results = []

        part_links = secici.select_attrs("li.parttab a", "href")
        if not part_links:
            part_links = [url]

        async def process_alt(vid: str, alt_name: str, ord_val: str) -> list[ExtractResult]:
            """Alternatif player kaynağından video linkini çıkarır."""
            with contextlib.suppress(Exception):
                resp = await self.httpx.post(
                    url  = f"{self.main_url}/player/ajax_sources.php",
                    data = {"vid": vid, "alternative": alt_name, "ord": ord_val}
                )
                if iframe_url := resp.json().get("iframe"):
                    data = await self.extract(self.fix_url(iframe_url))
                    if not data:
                        return []

                    return data if isinstance(data, list) else [data]

            return []

        async def process_part(part_url: str) -> list[ExtractResult]:
            """Her bir part sayfasını ve alternatiflerini işler."""
            try:
                # Elimizde zaten olan ana sayfayı tekrar çekmemek için
                if part_url == url:
                    sub_sec = secici
                else:
                    sub_resp = await self.httpx.get(part_url)
                    sub_sec  = HTMLHelper(sub_resp.text)

                iframe = sub_sec.select_attr("div#vast iframe", "src")
                if not iframe:
                    return []

                if self.main_url not in iframe:
                    data = await self.extract(self.fix_url(iframe))
                    if not data:
                        return []

                    return data if isinstance(data, list) else [data]

                # İç kaynaklı ise 3 alternatif için paralel istek at
                vid = iframe.split("vid=")[-1]
                tasks = [
                    process_alt(vid, "vidmoly", "0"),
                    process_alt(vid, "ok.ru", "1"),
                    process_alt(vid, "mailru", "2")
                ]

                alt_results = await asyncio.gather(*tasks)

                return [item for sublist in alt_results for item in sublist]
            except Exception:
                return []

        # Tüm partları paralel işle
        groups = await asyncio.gather(*(process_part(p) for p in part_links))

        for group in groups:
            results.extend(group)

        # Duplicate Temizliği
        unique_results = []
        seen = set()
        for res in results:
            if res.url and res.url not in seen:
                unique_results.append(res)
                seen.add(res.url)

        return unique_results
