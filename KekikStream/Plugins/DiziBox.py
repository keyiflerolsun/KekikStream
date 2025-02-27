# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import kekik_cache, PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode
from Kekik.Sifreleme  import CryptoJS
from parsel           import Selector
import re, urllib.parse, base64, contextlib, asyncio

class DiziBox(PluginBase):
    name        = "DiziBox"
    language    = "tr"
    main_url    = "https://www.dizibox.live"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Yabancı Dizi izle, Tüm yabancı dizilerin yeni ve eski sezonlarını full hd izleyebileceğiniz elit site."

    main_page   = {
        f"{main_url}/dizi-arsivi/page/SAYFA/?ulke[]=turkiye&yil=&imdb"   : "Yerli",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=aile&yil&imdb"       : "Aile",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=aksiyon&yil&imdb"    : "Aksiyon",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=animasyon&yil&imdb"  : "Animasyon",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=belgesel&yil&imdb"   : "Belgesel",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=bilimkurgu&yil&imdb" : "Bilimkurgu",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=biyografi&yil&imdb"  : "Biyografi",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=dram&yil&imdb"       : "Dram",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=drama&yil&imdb"      : "Drama",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=fantastik&yil&imdb"  : "Fantastik",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=gerilim&yil&imdb"    : "Gerilim",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=gizem&yil&imdb"      : "Gizem",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=komedi&yil&imdb"     : "Komedi",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=korku&yil&imdb"      : "Korku",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=macera&yil&imdb"     : "Macera",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=muzik&yil&imdb"      : "Müzik",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=muzikal&yil&imdb"    : "Müzikal",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=reality-tv&yil&imdb" : "Reality TV",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=romantik&yil&imdb"   : "Romantik",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=savas&yil&imdb"      : "Savaş",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=spor&yil&imdb"       : "Spor",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=suc&yil&imdb"        : "Suç",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=tarih&yil&imdb"      : "Tarih",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=western&yil&imdb"    : "Western",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur[0]=yarisma&yil&imdb"    : "Yarışma"
    }

    @kekik_cache(ttl=60*60)
    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek = await self.httpx.get(
            url              = f"{url.replace('SAYFA', str(page))}",
            follow_redirects = True
        )
        secici = Selector(istek.text)

        return [
            MainPageResult(
                category = category,
                title    = veri.css("h3 a::text").get(),
                url      = self.fix_url(veri.css("h3 a::attr(href)").get()),
                poster   = self.fix_url(veri.css("img::attr(src)").get()),
            )
                for veri in secici.css("article.detailed-article")
        ]

    @kekik_cache(ttl=60*60)
    async def search(self, query: str) -> list[SearchResult]:
        self.httpx.cookies.update({
            "LockUser"      : "true",
            "isTrustedUser" : "true",
            "dbxu"          : "1722403730363"
        })
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = Selector(istek.text)

        return [
            SearchResult(
                title  = item.css("h3 a::text").get(),
                url    = self.fix_url(item.css("h3 a::attr(href)").get()),
                poster = self.fix_url(item.css("img::attr(src)").get()),
            )
                for item in secici.css("article.detailed-article")
        ]

    @kekik_cache(ttl=60*60)
    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        title       = secici.css("div.tv-overview h1 a::text").get()
        poster      = self.fix_url(secici.css("div.tv-overview figure img::attr(src)").get())
        description = secici.css("div.tv-story p::text").get()
        year        = secici.css("a[href*='/yil/']::text").re_first(r"(\d{4})")
        tags        = secici.css("a[href*='/tur/']::text").getall()
        rating      = secici.css("span.label-imdb b::text").re_first(r"[\d.,]+")
        actors      = [actor.css("::text").get() for actor in secici.css("a[href*='/oyuncu/']")]

        episodes = []
        for sezon_link in secici.css("div#seasons-list a::attr(href)").getall():
            sezon_url    = self.fix_url(sezon_link)
            sezon_istek  = await self.httpx.get(sezon_url)
            sezon_secici = Selector(sezon_istek.text)

            for bolum in sezon_secici.css("article.grid-box"):
                ep_secici  = bolum.css("div.post-title a::text")

                ep_title   = ep_secici.get()
                ep_href    = self.fix_url(bolum.css("div.post-title a::attr(href)").get())
                ep_season  = ep_secici.re_first(r"(\d+)\. ?Sezon")
                ep_episode = ep_secici.re_first(r"(\d+)\. ?Bölüm")

                if ep_title and ep_href:
                    episodes.append(Episode(
                        season  = ep_season,
                        episode = ep_episode,
                        title   = ep_title,
                        url     = ep_href,
                    ))

        return SeriesInfo(
            url         = url,
            poster      = poster,
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            episodes    = episodes,
            actors      = actors,
        )

    @kekik_cache(ttl=60*60)
    async def _iframe_decode(self, name:str, iframe_link:str, referer:str) -> list[str]:
        results = []

        if "/player/king/king.php" in iframe_link:
            iframe_link = iframe_link.replace("king.php?v=", "king.php?wmode=opaque&v=")
            self.httpx.headers.update({"Referer": referer})

            istek  = await self.httpx.get(iframe_link)
            secici = Selector(istek.text)
            iframe = secici.css("div#Player iframe::attr(src)").get()

            self.httpx.headers.update({"Referer": self.main_url})
            istek = await self.httpx.get(iframe)

            crypt_data = re.search(r"CryptoJS\.AES\.decrypt\(\"(.*)\",\"", istek.text)[1]
            crypt_pass = re.search(r"\",\"(.*)\"\);", istek.text)[1]
            decode     = CryptoJS.decrypt(crypt_pass, crypt_data)

            if video_match := re.search(r"file: '(.*)',", decode):
                results.append(video_match[1])
            else:
                results.append(decode)

        elif "/player/moly/moly.php" in iframe_link:
            iframe_link = iframe_link.replace("moly.php?h=", "moly.php?wmode=opaque&h=")
            self.httpx.headers.update({"Referer": referer})
            while True:
                await asyncio.sleep(.3)
                with contextlib.suppress(Exception):
                    istek  = await self.httpx.get(iframe_link)

                    if atob_data := re.search(r"unescape\(\"(.*)\"\)", istek.text):
                        decoded_atob = urllib.parse.unquote(atob_data[1])
                        str_atob     = base64.b64decode(decoded_atob).decode("utf-8")

                    if iframe := Selector(str_atob).css("div#Player iframe::attr(src)").get():
                        results.append(iframe)

                    break

        elif "/player/haydi.php" in iframe_link:
            okru_url = base64.b64decode(iframe_link.split("?v=")[-1]).decode("utf-8")
            results.append(okru_url)

        return results

    @kekik_cache(ttl=15*60)
    async def load_links(self, url: str) -> list[str]:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        iframes = []
        if main_iframe := secici.css("div#video-area iframe::attr(src)").get():
            if decoded := await self._iframe_decode(self.name, main_iframe, url):
                iframes.extend(decoded)

        for alternatif in secici.css("div.video-toolbar option[value]"):
            alt_name = alternatif.css("::text").get()
            alt_link = alternatif.css("::attr(value)").get()

            if not alt_link:
                continue

            self.httpx.headers.update({"Referer": url})
            alt_istek = await self.httpx.get(alt_link)
            alt_istek.raise_for_status()

            alt_secici = Selector(alt_istek.text)
            if alt_iframe := alt_secici.css("div#video-area iframe::attr(src)").get():
                if decoded := await self._iframe_decode(alt_name, alt_iframe, url):
                    iframes.extend(decoded)

        return iframes