# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
from contextlib       import suppress

class DDizi(PluginBase):
    name        = "DDizi"
    language    = "tr"
    main_url    = "https://www.ddizi.im"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Ddizi, dizi izle, dizi seyret, yerli dizi izle, canlı dizi, türk dizi izle, dizi izle full, diziizle, eski diziler"

    main_page   = {
        f"{main_url}/yeni-eklenenler7"  : "Son Eklenen Bölümler",
        f"{main_url}/yabanci-dizi-izle" : "Yabancı Diziler",
        f"{main_url}/eski.diziler"      : "Eski Diziler",
        f"{main_url}/yerli-diziler"     : "Yerli Diziler"
    }

    async def get_articles(self, secici: HTMLHelper) -> list[dict]:
        articles = []
        for veri in secici.select("div.dizi-boxpost-cat, div.dizi-boxpost"):
            title  = veri.select_text("a")
            href   = veri.select_attr("a", "href")
            img    = veri.select_first("img.img-back, img.img-back-cat")
            poster = img.attrs.get("data-src") or img.attrs.get("src") if img else None

            if title and href:
                articles.append({
                    "title"  : title,
                    "url"    : self.fix_url(href),
                    "poster" : self.fix_url(poster),
                })

        return articles

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        # DDizi'de sayfalama /sayfa-X formatında (0'dan başlıyor)
        if page > 1:
            target_url = f"{url}/sayfa-{page-1}"
        else:
            target_url = url

        istek   = await self.httpx.get(target_url, follow_redirects=True)
        secici  = HTMLHelper(istek.text)
        veriler = await self.get_articles(secici)

        return [MainPageResult(**veri, category=category) for veri in veriler if veri]

    async def search(self, query: str) -> list[SearchResult]:
        istek = await self.httpx.post(
            url     = f"{self.main_url}/arama/",
            headers = {"Referer": f"{self.main_url}/"},
            data    = {"arama": query}
        )
        secici  = HTMLHelper(istek.text)
        veriler = await self.get_articles(secici)

        return [SearchResult(**veri) for veri in veriler if veri]

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("h1, h2, div.dizi-boxpost-cat a")
        poster      = secici.select_poster("div.afis img, img.afis, img.img-back, img.img-back-cat")
        description = secici.select_text("div.dizi-aciklama, div.aciklama, p")

        # DDizi'de doğru bir rating verisi yok
        # span.comments-ss yorum sayısı içeriyor, rating değil

        # Meta verileri (DDizi'de pek yok ama deniyoruz)
        # Year için sadece açıklama kısmına bakalım ki URL'deki ID'yi almasın
        year   = HTMLHelper(description).regex_first(r"(\d{4})") if description else None

        # Etiket ve Oyuncu iyileştirmesi
        tags   = secici.select_texts("div.tag-cloud a") or secici.select_texts("p.etiket a") or secici.select_texts("div.etiketler a")
        actors = secici.select_texts("div.oyuncular a") or secici.select_attrs("div.oyuncular img", "alt") or secici.select_texts("ul.bilgi li a")

        episodes     = []
        current_page = 1
        has_next     = True

        while has_next:
            page_url = f"{url}/sayfa-{current_page}" if current_page > 1 else url
            if current_page > 1:
                istek  = await self.httpx.get(page_url)
                secici = HTMLHelper(istek.text)

            page_eps = secici.select("div.bolumler a, div.sezonlar a, div.dizi-arsiv a, div.dizi-boxpost-cat a")
            if not page_eps:
                break

            for ep in page_eps:
                name = ep.text().strip()
                href = ep.attrs.get("href")
                if name and href:
                    # 'Bölüm Final' gibi durumları temizleyelim
                    clean_name = name.replace("Final", "").strip()
                    s, e = secici.extract_season_episode(clean_name)
                    episodes.append(Episode(
                        season  = s or 1,
                        episode = e or 1,
                        title   = name,
                        url     = self.fix_url(href)
                    ))

            # Sonraki sayfa kontrolü
            has_next = any("Sonraki" in a.text() for a in secici.select(".pagination a"))
            current_page += 1
            if current_page > 10:
                break # Emniyet kilidi

        if not episodes:
            s, e = secici.extract_season_episode(title)
            episodes.append(Episode(
                season  = s or 1,
                episode = e or 1,
                title   = title,
                url     = url
            ))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            rating      = None,
            year        = year,
            actors      = actors,
            episodes    = episodes
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        results = []
        # og:video ve JWPlayer kontrolü
        target_url = None

        # 1. og:video check
        og_video = secici.select_attr("meta[property='og:video']", "content")
        if og_video:
            target_url = self.fix_url(og_video)
        else:
            # 2. Iframe check (/player/oynat/...)
            iframe_src = secici.select_attr("iframe[src^='/player/oynat/']", "src")
            if iframe_src:
                target_url = self.fix_url(iframe_src)

        if target_url:
            with suppress(Exception):
                player_istek = await self.httpx.get(target_url, headers={"Referer": url})
                player_secici = HTMLHelper(player_istek.text)

                # file: '...' logic
                sources      = player_secici.regex_all(r'file:\s*["\']([^"\']+)["\']')
                extract_urls = []
                for src in sources:
                    src = self.fix_url(src)
                    # Direkt link kontrolü - Extractor gerektirmeyenler
                    is_direct = any(x in src.lower() for x in ["google", "twimg", "mncdn", "akamai", "streambox", ".m3u8", ".mp4", "master.txt"])

                    if is_direct:
                        results.append(ExtractResult(
                            url        = src,
                            name       = "Video",
                            user_agent = "googleusercontent",
                            referer    = "https://twitter.com/"
                        ))
                    else:
                        extract_urls.append(src)

                tasks = [self.extract(src, referer=target_url) for src in extract_urls]
                for res in await self.gather_with_limit(tasks):
                    self.collect_results(results, res)

                # Fallback to target_url itself if nothing found inside
                if not results:
                     if any(x in target_url.lower() for x in ["google", "twimg", "mncdn", "akamai", "streambox", ".m3u8", ".mp4", "master.txt"]) and ".html" not in target_url:
                        results.append(ExtractResult(
                            url        = target_url,
                            name       = "Video",
                            user_agent = "googleusercontent",
                            referer    = "https://twitter.com/"
                        ))
                     else:
                        res = await self.extract(target_url)
                        if res:
                            self.collect_results(results, res)

        return results
