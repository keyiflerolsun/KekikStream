# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper
import base64

class Sinezy(PluginBase):
    name        = "Sinezy"
    language    = "tr"
    main_url    = "https://sinezy.ink"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Yerli ve yabancı film izle! Türkçe Dublaj ve Alt Yazılı Seçenekleriyle full hd film izlemek için En çok tercih edilen adres!"

    main_page = {
        f"{main_url}/izle/en-yeni-filmler/"        : "Yeni Filmler",
        f"{main_url}/izle/en-yi-filmler/"          : "En İyi Filmler",
        f"{main_url}/izle/aksiyon-filmleri/"       : "Aksiyon ",
        f"{main_url}/izle/animasyon-filmleri/"     : "Animasyon",
        f"{main_url}/izle/belgesel-izle/"          : "Belgesel",
        f"{main_url}/izle/bilim-kurgu-filmleri/"   : "Bilim Kurgu ",
        f"{main_url}/izle/biyografi-filmleri/"     : "Biyografi ",
        f"{main_url}/izle/dram-filmleri/"          : "Dram",
        f"{main_url}/izle/erotik-film-izle/"       : "Erotik ",
        f"{main_url}/izle/fantastik-filmler/"      : "Fantastik",
        f"{main_url}/izle/gelecek-filmler/"        : "Yakında",
        f"{main_url}/izle/gerilim-filmleri/"       : "Gerilim ",
        f"{main_url}/izle/gizem-filmleri/"         : "Gizem ",
        f"{main_url}/izle/komedi-filmleri/"        : "Komedi ",
        f"{main_url}/izle/korku-filmleri/"         : "Korku ",
        f"{main_url}/izle/macera-filmleri/"        : "Macera ",
        f"{main_url}/izle/muzikal-izle/"           : "Müzikal",
        f"{main_url}/izle/romantik-film/"          : "Romantik ",
        f"{main_url}/izle/savas-filmleri/"         : "Savaş ",
        f"{main_url}/izle/spor-filmleri/"          : "Spor ",
        f"{main_url}/izle/suc-filmleri/"           : "Suç ",
        f"{main_url}/izle/tarih-filmleri/"         : "Tarih ",
        f"{main_url}/izle/turkce-altyazili-promo/" : "Altyazılı Pro",
        f"{main_url}/izle/yabanci-dizi/"           : "Yabancı Dizi",
        f"{main_url}/izle/en-iyi-filmler/"         : "En İyi Filmler",
        f"{main_url}/izle/en-yeni-filmler/"        : "Yeni Filmler",
        f"{main_url}/izle/yerli-filmler/"          : "Yerli Filmler",
        f"{main_url}/izle/yetiskin-film/"          : "Yetişkin +18",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}page/{page}/")
        secici = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.container div.content div.movie_box.move_k"):
            title  = secici.select_attr("a", "title", item)
            href   = secici.select_attr("a", "href", item)
            poster = secici.select_attr("img", "data-src", item)

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster)
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/arama/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.movie_box.move_k"):
            title  = secici.select_attr("a", "title", item)
            href   = secici.select_attr("a", "href", item)
            poster = secici.select_attr("img", "data-src", item)

            if title and href:
                results.append(SearchResult(
                    title   = title,
                    url     = self.fix_url(href),
                    poster  = self.fix_url(poster)
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_attr("div.detail", "title")
        poster      = secici.select_poster("div.move_k img")
        description = secici.select_text("div.desc.yeniscroll p")
        rating      = secici.select_text("span.info span.imdb")
        tags        = secici.select_texts("div.detail span a")
        actors      = secici.select_texts("span.oyn p")
        year        = secici.extract_year()
        duration    = secici.regex_first(r"(\d+) Dakika", secici.select_text("div.detail p"))

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

        encoded = secici.regex_first(r"ilkpartkod\s*=\s*'([^']+)'", secici.html)
        name    = secici.select_direct_text("li.pgrup a")
        if encoded:
            try:
                decoded     = base64.b64decode(encoded).decode('utf-8')
                decoded_sec = HTMLHelper(decoded)
                iframe      = decoded_sec.select_attr('iframe', 'src')

                if iframe:
                    iframe = self.fix_url(iframe)
                    data = await self.extract(iframe, name_override=name)
                    if data:
                        return [data]
            except Exception:
                pass

        return []
