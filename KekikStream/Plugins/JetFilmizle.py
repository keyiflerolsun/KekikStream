# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo
from parsel           import Selector

class JetFilmizle(PluginBase):
    name        = "JetFilmizle"
    language    = "tr"
    main_url    = "https://jetfilmizle.website"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Binlerce Film İzleme Seçeneğiyle En İyi Film İzleme Sitesi"

    main_page   = {
        f"{main_url}/page/"                                     : "Son Filmler",
        f"{main_url}/netflix/page/"                             : "Netflix",
        f"{main_url}/editorun-secimi/page/"                     : "Editörün Seçimi",
        f"{main_url}/turk-film-izle/page/"                      : "Türk Filmleri",
        f"{main_url}/cizgi-filmler-izle/page/"                  : "Çizgi Filmler",
        f"{main_url}/kategoriler/yesilcam-filmleri-izlee/page/" : "Yeşilçam Filmleri"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}{page}", follow_redirects=True)
        secici = Selector(istek.text)

        return [
            MainPageResult(
                category = category,
                title    = self.clean_title(veri.css("h2 a::text, h3 a::text, h4 a::text, h5 a::text, h6 a::text").get()),
                url      = self.fix_url(veri.css("a::attr(href)").get()),
                poster   = self.fix_url(veri.css("img::attr(data-src)").get() or veri.css("img::attr(src)").get()),
            )
                for veri in secici.css("article.movie") if veri.css("h2 a::text, h3 a::text, h4 a::text, h5 a::text, h6 a::text").get()
        ]

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.post(
            url     = f"{self.main_url}/filmara.php",
            data    = {"s": query},
            headers = {"Referer": f"{self.main_url}/"}
        )
        secici = Selector(istek.text)

        results = []
        for article in secici.css("article.movie"):
            title  = self.clean_title(article.css("h2 a::text, h3 a::text, h4 a::text, h5 a::text, h6 a::text").get())
            href   = article.css("a::attr(href)").get()
            poster = article.css("img::attr(data-src)").get() or article.css("img::attr(src)").get()

            if title and href:
                results.append(
                    SearchResult(
                        title  = title.strip(),
                        url    = self.fix_url(href.strip()),
                        poster = self.fix_url(poster.strip()) if poster else None,
                    )
                )

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        title       = self.clean_title(secici.css("div.movie-exp-title::text").get())
        poster_raw  = secici.css("section.movie-exp img::attr(data-src), section.movie-exp img::attr(src)").get()
        poster      = poster_raw.strip() if poster_raw else None
        
        desc_raw    = secici.css("section.movie-exp p.aciklama::text").get()
        description = desc_raw.strip() if desc_raw else None
        
        tags        = secici.css("section.movie-exp div.catss a::text").getall()
        
        rating_raw  = secici.css("section.movie-exp div.imdb_puan span::text").get()
        rating      = rating_raw.strip() if rating_raw else None
        
        year        = secici.xpath("//div[@class='yap' and (contains(., 'Vizyon') or contains(., 'Yapım'))]/text()").get()
        year        = year.strip() if year else None
        actors      = secici.css("div[itemprop='actor'] a span::text").getall()

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

    async def load_links(self, url: str) -> list[dict]:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        iframes = []
        if main_iframe := secici.css("div#movie iframe::attr(data-src), div#movie iframe::attr(data), div#movie iframe::attr(src)").get():
            iframes.append(self.fix_url(main_iframe))

        for part in secici.css("div.film_part a"):
            part_href = part.attrib.get("href")
            if not part_href:
                continue

            part_istek  = await self.httpx.get(part_href)
            part_secici = Selector(part_istek.text)

            if iframe := part_secici.css("div#movie iframe::attr(data-src), div#movie iframe::attr(data), div#movie iframe::attr(src)").get():
                iframes.append(self.fix_url(iframe))
            else:
                for link in part_secici.css("div#movie p a"):
                    if download_link := link.attrib.get("href"):
                        iframes.append(self.fix_url(download_link))

        processed_iframes = []
        for iframe in iframes:
            if "jetv.xyz" in iframe:
                jetv_istek  = await self.httpx.get(iframe)
                jetv_secici = Selector(jetv_istek.text)

                if jetv_iframe := jetv_secici.css("iframe::attr(src)").get():
                    processed_iframes.append(self.fix_url(jetv_iframe))
            else:
                processed_iframes.append(iframe)

        results = []
        for idx, iframe in enumerate(processed_iframes):
            extractor = self.ex_manager.find_extractor(iframe)
            results.append({
                "url"  : iframe,
                "name" : f"{extractor.name if extractor else f'Player {idx + 1}'}"
            })

        return results
