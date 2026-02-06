# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper

class DiziMom(PluginBase):
    name        = "DiziMom"
    language    = "tr"
    main_url    = "https://www.dizimom.art"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Binlerce yerli yabancı dizi arşivi, tüm sezonlar, kesintisiz bölümler. Sadece dizi izle, Dizimom heryerde seninle!"

    main_page = {
        f"{main_url}/tum-bolumler/page"               : "Son Bölümler",
        f"{main_url}/yerli-dizi-izle/page"            : "Yerli Diziler",
        f"{main_url}/yabanci-dizi-izle/page"          : "Yabancı Diziler",
        f"{main_url}/tv-programlari-izle/page"        : "TV Programları",
        f"{main_url}/netflix-dizileri-izle/page"      : "Netflix Dizileri",
        f"{main_url}/turkce-dublaj-diziler-hd/page"   : "Dublajlı Diziler",
        f"{main_url}/yerli-dizi-izle/page"            : "Yerli Diziler",
        f"{main_url}/anime-izle/page"                 : "Animeler",
        f"{main_url}/yabanci-dizi-izle/page"          : "Yabancı Diziler",
        f"{main_url}/kore-dizileri-izle-hd/page"      : "Kore Dizileri",
        f"{main_url}/full-hd-hint-dizileri-izle/page" : "Hint Dizileri",
        f"{main_url}/pakistan-dizileri-izle/page"     : "Pakistan Dizileri",
        f"{main_url}/tv-programlari-izle/page"        : "Tv Programları",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}/{page}/")
        secici = HTMLHelper(istek.text)

        results = []
        # Eğer "tum-bolumler" ise Episode kutularını, değilse Dizi kutularını tara
        if "/tum-bolumler/" in url:
            for item in secici.select("div.episode-box"):
                title = secici.select_text("div.episode-name a", item)
                href  = secici.select_attr("div.episode-name a", "href", item)
                img   = secici.select_poster("div.cat-img img", item)
                if title and href:
                    results.append(MainPageResult(
                        category = category,
                        title    = title.split(" izle")[0],
                        url      = self.fix_url(href),
                        poster   = self.fix_url(img)
                    ))
        else:
            for item in secici.select("div.single-item"):
                title = secici.select_text("div.categorytitle a", item)
                href  = secici.select_attr("div.categorytitle a", "href", item)
                img   = secici.select_poster("div.cat-img img", item)
                if title and href:
                    results.append(MainPageResult(
                        category = category,
                        title    = title.split(" izle")[0],
                        url      = self.fix_url(href),
                        poster   = self.fix_url(img)
                    ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)
        items  = secici.select("div.single-item")

        return [
            SearchResult(
                title  = secici.select_text("div.categorytitle a", item).split(" izle")[0],
                url    = self.fix_url(secici.select_attr("div.categorytitle a", "href", item)),
                poster = self.fix_url(secici.select_attr("div.cat-img img", "src", item))
            )
            for item in items
        ]

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = self.clean_title(secici.select_text("div.title h1"))
        poster      = secici.select_poster("div.category_image img")
        description = secici.select_direct_text("div.category_desc")
        tags        = secici.select_texts("div.genres a")
        rating      = secici.regex_first(r"(?s)IMDB\s*:\s*(?:</span>)?\s*([\d\.]+)", secici.html)
        year        = secici.extract_year("div.category_text")
        actors      = secici.meta_list("Oyuncular", container_selector="div#icerikcat2")

        episodes = []
        for item in secici.select("div.bolumust"):
            name = secici.select_text("div.baslik", item)
            href = secici.select_attr("a", "href", item)
            if name and href:
                s, e = secici.extract_season_episode(name)
                episodes.append(Episode(
                    season  = s or 1,
                    episode = e or 1,
                    title   = self.clean_title(name.replace(title, "").strip()),
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
        await self.httpx.post(
            url     = f"{self.main_url}/wp-login.php",
            headers = {
                "User-Agent"         : "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
                "sec-ch-ua"          : 'Not/A)Brand";v="8", "Chromium";v="137", "Google Chrome";v="137"',
                "sec-ch-ua-mobile"   : "?1",
                "sec-ch-ua-platform" : "Android"
            },
            data    = {
                "log"         : "keyiflerolsun",
                "pwd"         : "12345",
                "rememberme"  : "forever",
                "redirect_to" : self.main_url
            }
        )

        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        iframe_data = []

        # Aktif kaynağın (main iframe) adını bul
        current_name = secici.select_text("div.sources span.current_dil") or ""
        main_iframe  = secici.select_attr("iframe[src]", "src")

        # Bazen iframe doğrudan video p içinde olabilir
        if not main_iframe:
            main_iframe = secici.select_attr("div.video p iframe", "src")

        if main_iframe:
            iframe_data.append((main_iframe, current_name))

        # Diğer kaynakları (Partlar) gez
        sources = secici.select("div.sources a.post-page-numbers")
        for source in sources:
            href = secici.select_attr(None, "href", source)
            name = secici.select_text("span.dil", source)
            if href:
                # Part sayfasına git
                sub_istek  = await self.httpx.get(href)
                sub_helper = HTMLHelper(sub_istek.text)
                sub_iframe = sub_helper.select_attr("div.video p iframe", "src") or sub_helper.select_attr("iframe[src]", "src")

                if sub_iframe:
                    iframe_data.append((sub_iframe, name or f"{len(iframe_data)+1}.Kısım"))

        results = []
        for iframe_url, source_name in iframe_data:
            # URL düzeltme
            iframe_url = self.fix_url(iframe_url)

            # Prefix olarak kaynak adını kullan (1.Kısım | HDMomPlayer)
            extract_result = await self.extract(iframe_url, prefix=source_name)

            if extract_result:
                if isinstance(extract_result, list):
                    results.extend(extract_result)
                else:
                    results.append(extract_result)
            else:
                 results.append(ExtractResult(
                    url     = iframe_url,
                    name    = f"{source_name} | External",
                    referer = self.main_url
                ))

        return results
