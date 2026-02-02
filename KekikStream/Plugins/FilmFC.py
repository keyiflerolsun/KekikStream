# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper

class FilmFC(PluginBase):
    name        = "FilmFC"
    language    = "tr"
    main_url    = "https://www.filmfc.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Filmfc.com adresinden full hd kalitesiyle film izleme keyfine varacaksınız."

    main_page   = {
        f"{main_url}/erotikfilmler/abd-erotik/page"              : "ABD",
        f"{main_url}/erotikfilmler/alman-erotik/page"            : "Alman",
        f"{main_url}/erotikfilmler/erotik-filmler/page"          : "Erotik Filmler",
        f"{main_url}/erotikfilmler/fransiz-erotik/page"          : "Fransız",
        f"{main_url}/erotikfilmler/hint-erotik/page"             : "Hint",
        f"{main_url}/erotikfilmler/ispanyol-erotik/page"         : "İspanyol",
        f"{main_url}/erotikfilmler/italyan-erotik/page"          : "İtalyan",
        f"{main_url}/erotikfilmler/japon-erotik/page"            : "Japon",
        f"{main_url}/erotikfilmler/konulu-erotik/page"           : "Konulu",
        f"{main_url}/erotikfilmler/kore-erotik/page"             : "Kore",
        f"{main_url}/erotikfilmler/lezbiyen-erotik/page"         : "Lezbiyen",
        f"{main_url}/erotikfilmler/olgun-erotik/page"            : "Olgun",
        f"{main_url}/erotikfilmler/rus-erotik/page"              : "Rus",
        f"{main_url}/erotikfilmler/turkce-altyazili-erotik/page" : "Türkçe Altyazılı",
        f"{main_url}/erotikfilmler/turkce-dublaj-erotik/page"    : "Türkçe Dublaj",
        f"{main_url}/erotikfilmler/yabanci-erotik/page"          : "Yabancı",
        f"{main_url}/erotikfilmler/yerli-filmler/page"           : "Yerli Filmler",
        f"{main_url}/erotikfilmler/yesilcam-erotik/page"         : "Yeşilçam",
    }

    async def get_articles(self, secici: HTMLHelper) -> list[dict]:
        articles = []
        for veri in secici.select("div.icerik div.yan"):
            title  = secici.select_attr("a.baslik", "title", veri)
            href   = secici.select_attr("a.baslik", "href", veri)
            poster = secici.select_poster("img", veri)

            articles.append({
                "title" : self.clean_title(title),
                "url"   : self.fix_url(href),
                "poster": self.fix_url(poster),
            })

        return articles

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek   = await self.httpx.get(f"{url}/{page}")
        secici  = HTMLHelper(istek.text)
        veriler = await self.get_articles(secici)

        return [MainPageResult(**veri, category=category) for veri in veriler if veri]

    async def search(self, query: str) -> list[SearchResult]:
        istek   = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici  = HTMLHelper(istek.text)
        veriler = await self.get_articles(secici)

        return [SearchResult(**veri) for veri in veriler if veri]

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = self.clean_title(secici.select_text("div.bilgi h2"))
        poster      = secici.select_poster("div.resim img")
        year        = secici.select_text("div.bilgi a[href*=yil]")
        description = secici.select_direct_text("div.slayt-aciklama")
        tags        = secici.select_texts("p.tur a")
        rating      = secici.select_text("div.say p:nth-of-type(2)")
        rating      = rating.replace("BEĞEN", "") if rating else None
        duration    = secici.select_text("div.bilgi p b:nth-of-type(2)")
        duration    = duration.replace(" Dakika", "") if "dakika" in duration.lower() else None

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            duration    = duration
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        iframe = secici.select_attr("span#plyg iframe", "src")
        
        if not iframe:
            return []
            
        result = await self.extract(iframe, referer=url)

        return [result] if result else []
