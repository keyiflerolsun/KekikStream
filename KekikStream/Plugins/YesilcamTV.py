# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper

class YesilcamTV(PluginBase):
    name        = "YesilcamTV"
    language    = "tr"
    main_url    = "https://yesilcamtv.com.tr"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Yeşilçam'ın en güzel filmleri, restorasyonlu ve yüksek kalitede Yeşilçam TV'de."

    main_page   = {
        f"{main_url}/page/SAYFA/"                      : "Son Eklenenler",
        f"{main_url}/film-arsivi/page/SAYFA/"          : "Film Arşivi",
        f"{main_url}/category/aile/page/SAYFA/"        : "Aile",
        f"{main_url}/category/aksiyon/page/SAYFA/"     : "Aksiyon",
        f"{main_url}/category/belgesel/page/SAYFA/"    : "Belgesel",
        f"{main_url}/category/bilim-kurgu/page/SAYFA/" : "Bilim Kurgu",
        f"{main_url}/category/dram/page/SAYFA/"        : "Dram",
        f"{main_url}/category/fantastik/page/SAYFA/"   : "Fantastik",
        f"{main_url}/category/gerilim/page/SAYFA/"     : "Gerilim",
        f"{main_url}/category/gizem/page/SAYFA/"       : "Gizem",
        f"{main_url}/category/komedi/page/SAYFA/"      : "Komedi",
        f"{main_url}/category/korku/page/SAYFA/"       : "Korku",
        f"{main_url}/category/macera/page/SAYFA/"      : "Macera",
        f"{main_url}/category/muzik/page/SAYFA/"       : "Müzik",
        f"{main_url}/category/romantik/page/SAYFA/"    : "Romantik",
        f"{main_url}/category/savas/page/SAYFA/"       : "Savaş",
        f"{main_url}/category/suc/page/SAYFA/"         : "Suç",
        f"{main_url}/category/tarih/page/SAYFA/"       : "Tarih",
        f"{main_url}/category/tv-film/page/SAYFA/"     : "TV Film",
        f"{main_url}/category/vahsi-bati/page/SAYFA/"  : "Vahşi Batı",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(url.replace("SAYFA", str(page)))
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.listmovie"):
            title  = veri.select_text("div.film-ismi a")
            href   = veri.select_attr("div.film-ismi a", "href")
            poster = veri.select_attr("div.poster img", "data-src")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.listmovie"):
            title  = veri.select_text("div.film-ismi a")
            href   = veri.select_attr("div.film-ismi a", "href")
            poster = veri.select_attr("div.poster img", "data-src")

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("h1.title-border") or secici.select_text("div.title h1")
        poster      = secici.select_attr("div.film-afis img", "src") or secici.meta_value("og:image")
        description = secici.select_text("div#film-aciklama")
        tags        = secici.meta_list("Film Türü") or secici.select_texts("div#listelements div.elements a")
        rating      = secici.meta_value("IMDb") or secici.regex_first(r"IMDb:\s*(\d+\.?\d*)", istek.text)
        year        = secici.extract_year("div.list-item a[href*='/yil/']") or secici.meta_value("Yapım Yılı")
        actors      = secici.meta_list("Oyuncular") or secici.select_texts("div.list-item a[href*='/oyuncu/']")
        duration    = secici.extract_duration()

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors,
            duration    = duration
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        response = []

        # 1. Collect all iframes from the page
        iframes = secici.select("div.video iframe")
        if not iframes:
            iframes = secici.select("iframe[src*='rumble.com']")

        # 2. Extract labels for sources (Kaynak 1, Kaynak 2 etc.)
        labels = secici.select_texts("div.sources span.dil")

        # 3. Add results
        for i, iframe in enumerate(iframes):
            src = iframe.attrs.get("src")
            if not src:
                continue

            real_url = self.fix_url(src)
            label    = labels[i] if i < len(labels) else f"Kaynak {i+1}"

            data = await self.extract(real_url, referer=f"{self.main_url}/", prefix=label)
            self.collect_results(response, data)

        return self.deduplicate(response)
