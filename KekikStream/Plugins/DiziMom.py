# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
from json             import dumps, loads
import re

class DiziMom(PluginBase):
    name        = "DiziMom"
    language    = "tr"
    main_url    = "https://www.dizimom.one"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Binlerce yerli yabancı dizi arşivi, tüm sezonlar, kesintisiz bölümler. Sadece dizi izle, Dizimom heryerde seninle!"

    main_page = {
        f"{main_url}/tum-bolumler/page"        : "Son Bölümler",
        f"{main_url}/yerli-dizi-izle/page"     : "Yerli Diziler",
        f"{main_url}/yabanci-dizi-izle/page"   : "Yabancı Diziler",
        f"{main_url}/tv-programlari-izle/page" : "TV Programları",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        full_url = f"{url}/{page}/"
        istek    = await self.httpx.get(full_url)
        helper   = HTMLHelper(istek.text)

        results = []
        # Eğer "tum-bolumler" ise Episode kutularını, değilse Dizi kutularını tara
        if "/tum-bolumler/" in url:
            for item in helper.select("div.episode-box"):
                title = helper.select_text("div.episode-name a", item)
                href  = helper.select_attr("div.episode-name a", "href", item)
                img   = helper.select_poster("div.cat-img img", item)
                if title and href:
                    results.append(MainPageResult(category=category, title=title.split(" izle")[0], url=self.fix_url(href), poster=self.fix_url(img)))
        else:
            for item in helper.select("div.single-item"):
                title = helper.select_text("div.categorytitle a", item)
                href  = helper.select_attr("div.categorytitle a", "href", item)
                img   = helper.select_poster("div.cat-img img", item)
                if title and href:
                    results.append(MainPageResult(category=category, title=title.split(" izle")[0], url=self.fix_url(href), poster=self.fix_url(img)))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        url = f"{self.main_url}/?s={query}"
        istek = await self.httpx.get(url)
        helper = HTMLHelper(istek.text)
        items = helper.select("div.single-item")
        
        return [
            SearchResult(
                title  = helper.select_text("div.categorytitle a", item).split(" izle")[0],
                url    = self.fix_url(helper.select_attr("div.categorytitle a", "href", item)),
                poster = self.fix_url(helper.select_attr("div.cat-img img", "src", item))
            )
            for item in items
        ]

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        helper = HTMLHelper(istek.text)

        title       = self.clean_title(helper.select_text("div.title h1"))
        poster      = helper.select_poster("div.category_image img")
        description = helper.select_direct_text("div.category_desc")
        tags        = helper.select_texts("div.genres a")
        rating      = helper.regex_first(r"(?s)IMDB\s*:\s*(?:</span>)?\s*([\d\.]+)", helper.html)
        year        = helper.extract_year("div.category_text")
        actors      = helper.meta_list("Oyuncular", container_selector="div#icerikcat2")

        episodes = []
        for item in helper.select("div.bolumust"):
            name = helper.select_text("div.baslik", item)
            href = helper.select_attr("a", "href", item)
            if name and href:
                s, e = helper.extract_season_episode(name)
                episodes.append(Episode(
                    season  = s or 1,
                    episode = e or 1,
                    title   = self.clean_title(name.replace(title or "", "").strip()),
                    url     = self.fix_url(href)
                ))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster) if poster else None,
            title       = title or "Bilinmiyor",
            description = description,
            tags        = tags,
            rating      = rating,
            year        = str(year) if year else None,
            actors      = actors,
            episodes    = episodes
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        # Login simulation headers
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "sec-ch-ua": 'Not/A)Brand";v="8", "Chromium";v="137", "Google Chrome";v="137"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": "Android"
        }
        
        # Simulate login (as seen in Kotlin)
        login_url = f"{self.main_url}/wp-login.php"
        login_data = {
            "log": "keyiflerolsun",
            "pwd": "12345",
            "rememberme": "forever",
            "redirect_to": self.main_url
        }
        
        await self.httpx.post(login_url, headers=headers, data=login_data)
        
        istek = await self.httpx.get(url, headers=headers)
        helper = HTMLHelper(istek.text)
        
        iframes = []
        
        main_iframe = helper.select_attr("iframe[src]", "src")
        if main_iframe:
            iframes.append(main_iframe)
            
        sources = helper.select("div.sources a")
        for source in sources:
            href = source.attrs.get("href")
            if href:
                sub_istek = await self.httpx.get(href, headers=headers)
                sub_helper = HTMLHelper(sub_istek.text)
                sub_iframe = sub_helper.select_attr("div.video p iframe", "src")
                if sub_iframe:
                    iframes.append(sub_iframe)
                    
        results = []
        for iframe_url in iframes:
            # Check for known extractors
            if iframe_url.startswith("//"):
                iframe_url = f"https:{iframe_url}"
             
            extract_result = await self.extract(iframe_url)
            if extract_result:
                if isinstance(extract_result, list):
                    results.extend(extract_result)
                else:
                    results.append(extract_result)
            else:
                 results.append(ExtractResult(
                    url  = iframe_url,
                    name = f"{self.name} | External",
                    referer = self.main_url
                ))
                
        return results
