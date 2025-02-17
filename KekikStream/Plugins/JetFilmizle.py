# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, SearchResult, MovieInfo
from parsel           import Selector

class JetFilmizle(PluginBase):
    name     = "JetFilmizle"
    main_url = "https://jetfilmizle.io"

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.oturum.post(
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
        istek  = await self.oturum.get(url)
        secici = Selector(istek.text)

        title       = self.clean_title(secici.css("div.movie-exp-title::text").get())
        poster      = secici.css("section.movie-exp img::attr(data-src), section.movie-exp img::attr(src)").get().strip()
        description = secici.css("section.movie-exp p.aciklama::text").get().strip()
        tags        = secici.css("section.movie-exp div.catss a::text").getall()
        rating      = secici.css("section.movie-exp div.imdb_puan span::text").get().strip()
        year        = secici.xpath("//div[@class='yap' and (contains(., 'Vizyon') or contains(., 'Yapım'))]/text()").get().strip()
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

    async def load_links(self, url: str) -> list[str]:
        istek  = await self.oturum.get(url)
        secici = Selector(istek.text)

        iframes = []
        if main_iframe := secici.css("div#movie iframe::attr(data-src), div#movie iframe::attr(data), div#movie iframe::attr(src)").get():
            iframes.append(self.fix_url(main_iframe))

        for part in secici.css("div.film_part a"):
            part_href = part.attrib.get("href")
            if not part_href:
                continue

            part_istek  = await self.oturum.get(part_href)
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
                jetv_istek  = await self.oturum.get(iframe)
                jetv_secici = Selector(jetv_istek.text)

                if jetv_iframe := jetv_secici.css("iframe::attr(src)").get():
                    processed_iframes.append(self.fix_url(jetv_iframe))
            else:
                processed_iframes.append(iframe)

        return processed_iframes