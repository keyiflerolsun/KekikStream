# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper
import asyncio

class FilmEkseni(PluginBase):
    name        = "FilmEkseni"
    language    = "tr"
    main_url    = "https://filmekseni.cc"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Film Ekseni ⚡️ Vizyonda ki, en güncel ve en yeni filmleri full hd kalitesinde türkçe dublaj ve altyazı seçenekleriyle 1080p olarak izleyebileceğiniz adresiniz."

    main_page = {
        f"{main_url}/tur/aile-filmleri/page"        : "Aile Filmleri",
        f"{main_url}/tur/aksiyon-filmleri/page"     : "Aksiyon Filmleri",
        f"{main_url}/tur/animasyon-film-izle/page"  : "Animasyon Filmleri",
        f"{main_url}/tur/bilim-kurgu-filmleri/page" : "Bilim Kurgu Filmleri",
        f"{main_url}/tur/biyografi-filmleri/page"   : "Biyografi Filmleri",
        f"{main_url}/tur/dram-filmleri-izle/page"   : "Dram Filmleri",
        f"{main_url}/tur/fantastik-filmler/page"    : "Fantastik Filmleri",
        f"{main_url}/tur/gerilim-filmleri/page"     : "Gerilim Filmleri",
        f"{main_url}/tur/gizem-filmleri/page"       : "Gizem Filmleri",
        f"{main_url}/tur/komedi-filmleri/page"      : "Komedi Filmleri",
        f"{main_url}/tur/korku-filmleri/page"       : "Korku Filmleri",
        f"{main_url}/tur/macera-filmleri/page"      : "Macera Filmleri",
        f"{main_url}/tur/romantik-filmler/page"     : "Romantik Filmleri",
        f"{main_url}/tur/savas-filmleri/page"       : "Savaş Filmleri",
        f"{main_url}/tur/suc-filmleri/page"         : "Suç Filmleri",
        f"{main_url}/tur/tarih-filmleri/page"       : "Tarih Filmleri",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek   = await self.httpx.get(f"{url}/{page}/")
        secici  = HTMLHelper(istek.text)
        posters = secici.select("div.poster")

        return [
            MainPageResult(
                category = category,
                title    = self.clean_title(secici.select_text("h2", veri)),
                url      = secici.select_attr("a", "href", veri),
                poster   = secici.select_attr("img", "data-src", veri)
            )
                for veri in posters
        ]

    async def search(self, query: str) -> list[SearchResult]:
        istek = await self.httpx.post(
            url     = f"{self.main_url}/search/",
            headers = {
                "X-Requested-With" : "XMLHttpRequest",
                "Content-Type"     : "application/x-www-form-urlencoded; charset=UTF-8",
                "Referer"          : self.main_url,
            },
            data    = {"query": query}
        )

        veriler = istek.json().get("result", [])

        return [
            SearchResult(
                title  = veri.get("title"),
                url    = f"{self.main_url}/{veri.get('slug')}",
                poster = f"{self.main_url}/uploads/poster/{veri.get('cover')}" if veri.get('cover') else None,
            )
                for veri in veriler
        ]

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = self.clean_title(secici.select_text("div.page-title h1"))
        poster      = secici.select_poster("picture.poster-auto img")
        description = secici.select_direct_text("article.text-white p")
        year        = secici.extract_year("div.page-title", "strong a")
        tags        = secici.select_texts("div.pb-2 a[href*='/tur/']")
        rating      = secici.select_text("div.rate")
        duration    = secici.regex_first(r"(\d+)", secici.select_text("div.d-flex.flex-column.text-nowrap"))
        actors      = secici.select_texts("div.card-body.p-0.pt-2 .story-item .story-item-title")

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

    async def _get_source_links(self, name: str, url: str, is_active: bool, initial_helper: HTMLHelper | None = None) -> list[ExtractResult]:
        try:
            if is_active and initial_helper:
                secici = initial_helper
            else:
                resp   = await self.httpx.get(url)
                secici = HTMLHelper(resp.text)

            iframe = secici.select_first("div.card-video iframe")
            if not iframe:
                return []

            iframe_url = iframe.attrs.get("data-src") or iframe.attrs.get("src")
            if not iframe_url:
                return []

            iframe_url = self.fix_url(iframe_url)
            results    = []

            # VIP / EksenLoad mantığı
            if "eksenload" in iframe_url or name == "VIP":
                video_id   = iframe_url.split("/")[-1]
                master_url = f"https://eksenload.site/uploads/encode/{video_id}/master.m3u8"
                results.append(ExtractResult(
                    url     = master_url,
                    name    = name,
                    referer = self.main_url
                ))
            else:
                # Diğerleri (Moly, vs.) için extract
                # Name override: "Kaynak Adı | Player Adı" olacak şekilde
                extracted = await self.extract(iframe_url, name_override=name)
                if extracted:
                    if isinstance(extracted, list):
                        results.extend(extracted)
                    else:
                        results.append(extracted)

            return results
        except Exception:
            return []

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        sources = [] # (name, url, is_active)
        if nav_links := secici.select("nav.card-nav a.nav-link"):
            seen_urls = set()
            for link in nav_links:
                if link.attrs.get("href") == "#":
                    continue # Sinema Modu vb.

                name      = link.text(strip=True)
                href      = link.attrs.get("href")
                is_active = "active" in link.attrs.get("class", "")

                if href and href not in seen_urls:
                    seen_urls.add(href)
                    sources.append((name, href, is_active))
        else:
            # Nav yoksa mevcut sayfayı (Varsayılan/VIP) al
            sources.append(("VIP", url, True))

        tasks = []
        for name, link_url, is_active in sources:
            tasks.append(self._get_source_links(name, link_url, is_active, secici if is_active else None))

        return [item for sublist in await asyncio.gather(*tasks) for item in sublist]
