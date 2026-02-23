# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
from Kekik.Sifreleme  import CryptoJS
import urllib.parse, base64, contextlib, asyncio, time

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

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        self.httpx.cookies.update({
            "isTrustedUser" : "true",
            "dbxu"          : str(time.time() * 1000).split(".")[0]
        })
        istek = await self.httpx.get(
            url              = f"{url.replace('SAYFA', str(page))}",
            follow_redirects = True
        )
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("article.detailed-article"):
            title  = veri.select_text("h3 a")
            href   = veri.select_attr("h3 a", "href")
            poster = veri.select_attr("img", "src")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        self.httpx.cookies.update({
            "isTrustedUser" : "true",
            "dbxu"          : str(time.time() * 1000).split(".")[0]
        })
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for item in secici.select("article.detailed-article"):
            title  = item.select_text("h3 a")
            href   = item.select_attr("h3 a", "href")
            poster = item.select_attr("img", "src")

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("div.tv-overview h1 a")
        poster      = secici.select_poster("div.tv-overview figure img")
        description = secici.select_text("div.tv-story p")
        year        = secici.extract_year("a[href*='/yil/']")
        tags        = secici.select_texts("a[href*='/tur/']")
        rating      = secici.regex_first(r"[\d.,]+", secici.select_text("span.label-imdb b"))
        actors      = secici.select_texts("a[href*='/oyuncu/']")

        episodes = []
        for link in secici.select_attrs("div#seasons-list a", "href"):
            r        = await self.httpx.get(self.fix_url(link))
            s_secici = HTMLHelper(r.text)
            for bolum in s_secici.select("article.grid-box"):
                name = bolum.select_text("div.post-title a")
                href = bolum.select_attr("div.post-title a", "href")
                if name and href:
                    s, e = s_secici.extract_season_episode(name)
                    episodes.append(Episode(season=s, episode=e, title=name, url=self.fix_url(href)))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            episodes    = episodes,
            actors      = actors,
        )

    async def _iframe_decode(self, name:str, iframe_link:str, referer:str) -> list[str]:
        results = []

        self.httpx.headers.update({"Referer": referer})
        self.httpx.cookies.update({
            "isTrustedUser" : "true",
            "dbxu"          : str(time.time() * 1000).split(".")[0]
        })

        if "/player/king/king.php" in iframe_link:
            iframe_link = iframe_link.replace("king.php?v=", "king.php?wmode=opaque&v=")

            istek  = await self.httpx.get(iframe_link)
            secici = HTMLHelper(istek.text)
            iframe = secici.select_attr("div  #Player iframe", "src")

            if iframe:
                self.httpx.headers.update({"Referer": self.main_url})
                iframe_istek = await self.httpx.get(iframe)
                iframe_secici = HTMLHelper(iframe_istek.text)

                crypt_data = iframe_secici.regex_first(r"CryptoJS\.AES\.decrypt\(\"(.*)\",\"", iframe_istek.text)
                crypt_pass = iframe_secici.regex_first(r"\",\"(.*)\"\);", iframe_istek.text)
                decode     = CryptoJS.decrypt(crypt_pass, crypt_data)

                if video_match := iframe_secici.regex_first(r"file: '(.*)',", decode):
                    results.append(video_match)
                else:
                    results.append(decode)

        elif "/player/moly/moly.php" in iframe_link:
            iframe_link = iframe_link.replace("moly.php?h=", "moly.php?wmode=opaque&h=")
            while True:
                await asyncio.sleep(.3)
                with contextlib.suppress(Exception):
                    moly_istek  = await self.httpx.get(iframe_link)
                    moly_secici = HTMLHelper(moly_istek.text)

                    if atob_data := moly_secici.regex_first(r"unescape\(\"(.*)\"\)", moly_istek.text):
                        decoded_atob = urllib.parse.unquote(atob_data)
                        str_atob     = base64.b64decode(decoded_atob).decode("utf-8")

                        iframe_src = HTMLHelper(str_atob).select_attr("div#Player iframe", "src")
                        if iframe_src:
                            results.append(iframe_src)

                    break

        elif "/player/haydi.php" in iframe_link:
            okru_url = base64.b64decode(iframe_link.split("?v=")[-1]).decode("utf-8")
            results.append(okru_url)

        return results

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        # Aktif kaynağın adını bul (DBX Pro vs.)
        current_source_name = secici.select_text("div.video-toolbar option[selected]") or self.name

        results     = []
        main_iframe = secici.select_attr("div  #video-area iframe", "src")

        if main_iframe:
            if decoded := await self._iframe_decode(self.name, main_iframe, url):
                tasks = [self.extract(iframe, name_override=current_source_name) for iframe in decoded]
                for data in await self.gather_with_limit(tasks):
                    self.collect_results(results, data)

        for alternatif in secici.select("div.video-toolbar option[value]"):
            alt_name = alternatif.select_text(None)
            alt_link = alternatif.select_attr(None, "value")

            if not alt_link:
                continue

            self.httpx.headers.update({"Referer": url})
            alt_istek = await self.httpx.get(alt_link)
            alt_istek.raise_for_status()

            alt_secici = HTMLHelper(alt_istek.text)
            alt_iframe = alt_secici.select_attr("div  #video-area iframe", "src")

            if alt_iframe:
                if decoded := await self._iframe_decode(alt_name, alt_iframe, url):
                    tasks = [self.extract(iframe, name_override=alt_name) for iframe in decoded]
                    for data in await self.gather_with_limit(tasks):
                        self.collect_results(results, data)

        return results
