# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper
import asyncio

class SuperFilmIzle(PluginBase):
    name        = "SuperFilmIzle"
    language    = "tr"
    main_url    = "https://superfilmizle.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Superfilmizle ile HD Kalite film izle türkçe altyazılı olarak super kalitede donmadan izleyin."

    main_page   = {
        f"{main_url}/category/aile-filmleri/page/"		: "Aile Filmleri",
        f"{main_url}/category/aksiyon-filmleri/page/"	: "Aksiyon Filmleri",
        f"{main_url}/category/animasyon-filmleri/page/"	: "Animasyon Filmleri",
        f"{main_url}/category/bilim-kurgu/page/"		: "Bilim Kurgu",
        f"{main_url}/category/biyografi-filmleri/page/"	: "Biyografi Filmleri",
        f"{main_url}/category/dram-filmleri/page/"		: "Dram Filmleri",
        f"{main_url}/category/editor-secim/page/"		: "Editör Seçim",
        f"{main_url}/category/erotik-film/page/"		: "Erotik Film",
        f"{main_url}/category/fantastik-filmler/page/"	: "Fantastik Filmler",
        f"{main_url}/category/gelecek-filmler/page/"	: "Gelecek Filmler",
        f"{main_url}/category/gerilim-filmleri/page/"	: "Gerilim Filmleri",
        f"{main_url}/category/hint-filmleri/page/"		: "Hint Filmleri",
        f"{main_url}/category/komedi-filmleri/page/"	: "Komedi Filmleri",
        f"{main_url}/category/kore-filmleri/page/"		: "Kore Filmleri",
        f"{main_url}/category/korku-filmleri/page/"		: "Korku Filmleri",
        f"{main_url}/category/macera-filmleri/page/"	: "Macera Filmleri",
        f"{main_url}/category/muzikal-filmler/page/"	: "Müzikal Filmler",
        f"{main_url}/category/romantik-filmler/page/"	: "Romantik Filmler",
        f"{main_url}/category/savas-filmleri/page/"		: "Savaş Filmleri",
        f"{main_url}/category/spor-filmleri/page/"		: "Spor Filmleri",
        f"{main_url}/category/suc-filmleri/page/"		: "Suç Filmleri",
        f"{main_url}/category/tarih-filmleri/page/"		: "Tarih Filmleri",
        f"{main_url}/category/western-filmleri/page/"	: "Western Filmleri",
        f"{main_url}/category/yerli-filmler/page/"		: "Yerli Filmler",
        f"{main_url}/category/yetiskin-filmleri/page/"	: "Yetişkin Filmleri"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}{page}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movie-box"):
            title_text = secici.select_text("div.name a", veri)
            if not title_text:
                continue

            href   = secici.select_attr("div.name a", "href", veri)
            poster = secici.select_poster("img", veri)

            results.append(MainPageResult(
                category = category,
                title    = self.clean_title(title_text),
                url      = self.fix_url(href),
                poster   = self.fix_url(poster),
            ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movie-box"):
            title_text = secici.select_text("div.name a", veri)
            if not title_text:
                continue

            href   = secici.select_attr("div.name a", "href", veri)
            poster = secici.select_poster("img", veri)

            results.append(SearchResult(
                title  = self.clean_title(title_text),
                url    = self.fix_url(href),
                poster = self.fix_url(poster),
            ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = self.clean_title(secici.select_text("div.film h1"))
        poster      = secici.select_poster("div.poster img")
        year        = secici.extract_year("div.release a")
        description = secici.select_direct_text("div.description")
        tags        = secici.select_texts("ul.post-categories li a")
        rating      = secici.select_text("div.imdb-count")
        rating      = rating.replace("IMDB Puanı", "") if rating else None
        actors      = secici.select_texts("div.actors a") or secici.select_texts("div.cast a")

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek     = await self.httpx.get(url)
        main_text = istek.text
        secici    = HTMLHelper(main_text)

        # 1. Alternatifleri / Parçaları Belirle
        # (url, name, needs_fetch)
        sources = []

        # Keremiya / Movifox Alternatif Yapısı (li.part)
        part_items = secici.select("div#action-parts li.part")
        if part_items:
            for li in part_items:
                name = secici.select_text("div.part-name", li) or "Alternatif"

                # Aktif olan parça (Mevcut sayfada)
                if "active" in li.attrs.get("class", []):
                    sources.append((None, name, False))

                # Pasif olanlar (Link verilmişse)
                elif a_tag := secici.select_first("a.post-page-numbers", li):
                    href = a_tag.attrs.get("href")
                    if href:
                        sources.append((self.fix_url(href), name, True))
        else:
            # Alternatif menüsü yoksa tek parça olarak işle
            sources.append((None, "", False))

        # 2. İşleme Görevlerini Hazırla
        extract_tasks = []

        async def process_task(source_data):
            src_url, src_name, needs_fetch = source_data

            # Iframe'i bulacağımız HTML kaynağını belirle
            html_to_parse = main_text
            if needs_fetch:
                try:
                    resp = await self.httpx.get(src_url)
                    html_to_parse = resp.text
                except:
                    return []

            # HTML içindeki iframeleri topla
            temp_secici = HTMLHelper(html_to_parse)
            iframes = []
            for ifr in temp_secici.select("div.video-content iframe"):
                if src := ifr.attrs.get("src") or ifr.attrs.get("data-src"):
                    iframes.append(self.fix_url(src))

            # Bulunan iframeleri extract et (prefix olarak parça adını ekle)
            results = []
            for ifr_url in iframes:
                if extracted := await self.extract(ifr_url, prefix=src_name or None):
                    if isinstance(extracted, list):
                        results.extend(extracted)
                    else:
                        results.append(extracted)
            return results

        for src in sources:
            extract_tasks.append(process_task(src))

        # 3. Tüm Görevleri Paralel Çalıştır ve Sonuçları Topla
        results_groups = await asyncio.gather(*extract_tasks)

        final_results = []
        for group in results_groups:
            final_results.extend(group)

        return final_results
