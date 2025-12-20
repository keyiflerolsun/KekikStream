# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo
from parsel           import Selector

class JetFilmizle(PluginBase):
    name        = "JetFilmizle"
    language    = "tr"
    main_url    = "https://jetfilmizle.website"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Film izle, Yerli, Yabancı film izle, Türkçe dublaj, alt yazılı seçenekleriyle ödül almış filmleri Full HD kalitesiyle ve jetfilmizle hızıyla donmadan ücretsizce izleyebilirsiniz."

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
        
        
        # Year - div.yap içinde 4 haneli sayı ara
        year_div = secici.xpath("//div[@class='yap' and (contains(., 'Vizyon') or contains(., 'Yapım'))]/text()").get()
        year = None
        if year_div:
            year_match = re.search(r'(\d{4})', year_div.strip())
            if year_match:
                year = year_match.group(1)
        
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

        results = []

        # 1) Ana iframe'leri kontrol et
        for iframe in secici.css("iframe"):
            src = (iframe.css("::attr(src)").get() or 
                   iframe.css("::attr(data-src)").get() or
                   iframe.css("::attr(data-lazy-src)").get())
            
            if src and src != "about:blank":
                iframe_url = self.fix_url(src)
                extractor = self.ex_manager.find_extractor(iframe_url)
                results.append({
                    "url": iframe_url,
                    "name": extractor.name if extractor else "Ana Player"
                })

        # 2) Sayfa numaralarından linkleri topla (Fragman hariç)
        page_links = []
        for link in secici.css("a.post-page-numbers"):
            isim = link.css("span::text").get() or ""
            if isim != "Fragman":
                href = link.css("::attr(href)").get()
                if href:
                    page_links.append((self.fix_url(href), isim))

        # 3) Her sayfa linkindeki iframe'leri bul
        for page_url, isim in page_links:
            try:
                page_resp = await self.httpx.get(page_url)
                page_sel = Selector(page_resp.text)
                
                for iframe in page_sel.css("div#movie iframe"):
                    src = (iframe.css("::attr(src)").get() or 
                           iframe.css("::attr(data-src)").get() or
                           iframe.css("::attr(data-lazy-src)").get())
                    
                    if src and src != "about:blank":
                        iframe_url = self.fix_url(src)
                        extractor = self.ex_manager.find_extractor(iframe_url)
                        results.append({
                            "url": iframe_url,
                            "name": f"{extractor.name if extractor else 'Player'} | {isim}"
                        })
            except Exception:
                continue

        return results
