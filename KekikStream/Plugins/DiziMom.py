# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re

class DiziMom(PluginBase):
    name        = "DiziMom"
    language    = "tr"
    main_url    = "https://www.dizimom.pw"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Binlerce yerli yabancı dizi arşivi, tüm sezonlar, kesintisiz bölümler. Sadece dizi izle, Dizimom heryerde seninle!"

    main_page = {
        f"{main_url}/tum-bolumler/page"               : "Son Bölümler",
        f"{main_url}/yerli-dizi-izle/page"            : "Yerli Diziler",
        f"{main_url}/yabanci-dizi-izle/page"          : "Yabancı Diziler",
        f"{main_url}/tv-programlari-izle/page"        : "TV Programları",
        f"{main_url}/netflix-dizileri-izle/page"      : "Netflix Dizileri",
        f"{main_url}/turkce-dublaj-diziler-hd/page"   : "Dublajlı Diziler",
        f"{main_url}/anime-izle/page"                 : "Animeler",
        f"{main_url}/kore-dizileri-izle-hd/page"      : "Kore Dizileri",
        f"{main_url}/full-hd-hint-dizileri-izle/page" : "Hint Dizileri",
        f"{main_url}/pakistan-dizileri-izle/page"     : "Pakistan Dizileri",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.async_cf_get(f"{url}/{page}/")
        secici = HTMLHelper(istek.text)

        results = []
        # Eğer "tum-bolumler" ise Episode kutularını, değilse Dizi kutularını tara
        if "/bolum" in url or "tum-bolumler" in url:
            for item in secici.select("div.episode-box"):
                title = item.select_text("div.episode-name a")
                href  = item.select_attr("div.episode-name a", "href")
                img   = item.select_poster("div.cat-img img")
                if title and href:
                    results.append(MainPageResult(
                        category = category,
                        title    = title.split(" izle")[0],
                        url      = self.fix_url(href),
                        poster   = self.fix_url(img)
                    ))
        else:
            for item in secici.select("div.single-item"):
                title = item.select_text("div.categorytitle a")
                href  = item.select_attr("div.categorytitle a", "href")
                img   = item.select_poster("div.cat-img img")
                if title and href:
                    results.append(MainPageResult(
                        category = category,
                        title    = title.split(" izle")[0],
                        url      = self.fix_url(href),
                        poster   = self.fix_url(img)
                    ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.async_cf_get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)
        items  = secici.select("div.single-item")

        results = []
        for item in items:
            title_node = item.select_first("div.categorytitle a")
            if not title_node:
                continue

            title = title_node.text(strip=True).split(" izle")[0]
            href  = title_node.attrs.get("href")
            img   = item.select_poster("div.cat-img img")

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(img)
                ))
        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("div.title h1") or secici.select_text("h1")
        poster      = secici.select_poster("div.category_image img") or secici.meta_value("og:image")
        description = secici.select_direct_text("div.category_desc") or secici.meta_value("og:description")
        tags        = secici.select_texts("div.genres a")
        rating      = secici.regex_first(r"(?s)IMDB\s*:\s*(?:</span>)?\s*([\d\.]+)", secici.html)
        year        = secici.extract_year("div.category_text")
        actors      = secici.meta_list("Oyuncular", container_selector="div  #icerikcat2")

        if not rating:
            rating = secici.regex_first(r'"aggregateRating"\s*:\s*\{[\s\S]*?"ratingValue"\s*:\s*"([\d\.]+)"')

        episodes = []
        for item in secici.select("div.bolumust"):
            name = item.select_text("div.baslik")
            href = item.select_attr("a", "href")
            if name and href:
                s, e = secici.extract_season_episode(name)
                episodes.append(Episode(
                    season  = s or 1,
                    episode = e or 1,
                    title   = name.replace(title or "", "").strip(),
                    url     = self.fix_url(href)
                ))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors,
            episodes    = episodes
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        # Login işlemi bazen Cloudflare yüzünden async_cf_post gerektirebilir
        await self.async_cf_post(
            url  = f"{self.main_url}/wp-login.php",
            data = {
                "log"         : "keyiflerolsun",
                "pwd"         : "12345",
                "rememberme"  : "forever",
                "redirect_to" : self.main_url
            }
        )

        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        iframe_data = []

        # Aktif kaynağın (main iframe) adını bul
        current_name = secici.select_text("div.sources span.current_dil") or ""
        main_iframe  = secici.select_attr("iframe[src]", "src")
        if main_iframe == "about:blank":
            main_iframe = None

        # Bazen iframe doğrudan video p içinde olabilir
        if not main_iframe:
            main_iframe = secici.select_attr("div.video p iframe", "src")

        if main_iframe == "about:blank":
            main_iframe = None

        if not main_iframe:
            main_iframe = secici.regex_first(r'<iframe[^>]+src=["\'](?!about:blank)([^"\']+)')

        if main_iframe:
            iframe_data.append((main_iframe, current_name or "Varsayılan"))

        # Diğer kaynakları (Partlar) gez
        sources = secici.select("div.sources a.post-page-numbers")
        for source in sources:
            href = source.select_attr(None, "href")
            name = source.select_text("span.dil")
            if href:
                # Part sayfasına git
                sub_istek  = await self.httpx.get(href)
                sub_helper = HTMLHelper(sub_istek.text)
                sub_iframe = sub_helper.select_attr("div.video p iframe", "src") or sub_helper.select_attr("iframe[src]", "src")

                if sub_iframe == "about:blank":
                    sub_iframe = None

                if not sub_iframe:
                    sub_iframe = sub_helper.regex_first(r'<iframe[^>]+src=["\'](?!about:blank)([^"\']+)')

                if sub_iframe:
                    iframe_data.append((sub_iframe, name or f"{len(iframe_data)+1}.Kısım"))

        async def _extract_or_fallback(iframe_url, source_name):
            iframe_url = self.fix_url(iframe_url)
            if not iframe_url or iframe_url == "about:blank" or iframe_url.startswith("javascript:"):
                return None
            result = await self.extract(iframe_url, name_override=source_name)
            if result:
                return result
            return ExtractResult(url=iframe_url, name=f"{source_name} | External", referer=self.main_url)

        tasks   = [_extract_or_fallback(url, name) for url, name in iframe_data]
        results = []
        for data in await self.gather_with_limit(tasks):
            self.collect_results(results, data)

        return results
