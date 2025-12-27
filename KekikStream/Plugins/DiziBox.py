# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult
from Kekik.Sifreleme   import CryptoJS
from selectolax.parser import HTMLParser
import re, urllib.parse, base64, contextlib, asyncio, time

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
        secici = HTMLParser(istek.text)

        results = []
        for veri in secici.css("article.detailed-article"):
            h3_link = veri.css_first("h3 a")
            img_el  = veri.css_first("img")

            title  = h3_link.text(strip=True) if h3_link else None
            href   = h3_link.attrs.get("href") if h3_link else None
            poster = img_el.attrs.get("src") if img_el else None

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster) if poster else None,
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        self.httpx.cookies.update({
            "isTrustedUser" : "true",
            "dbxu"          : str(time.time() * 1000).split(".")[0]
        })
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLParser(istek.text)

        results = []
        for item in secici.css("article.detailed-article"):
            h3_link = item.css_first("h3 a")
            img_el  = item.css_first("img")

            title  = h3_link.text(strip=True) if h3_link else None
            href   = h3_link.attrs.get("href") if h3_link else None
            poster = img_el.attrs.get("src") if img_el else None

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster) if poster else None,
                ))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)

        title_el = secici.css_first("div.tv-overview h1 a")
        title    = title_el.text(strip=True) if title_el else None

        poster_el = secici.css_first("div.tv-overview figure img")
        poster    = poster_el.attrs.get("src") if poster_el else None

        desc_el     = secici.css_first("div.tv-story p")
        description = desc_el.text(strip=True) if desc_el else None

        # year: re_first yerine re.search
        year_el = secici.css_first("a[href*='/yil/']")
        year_text = year_el.text(strip=True) if year_el else ""
        year_match = re.search(r"(\d{4})", year_text)
        year = year_match.group(1) if year_match else None

        tags = [a.text(strip=True) for a in secici.css("a[href*='/tur/']") if a.text(strip=True)]

        # rating: re_first yerine re.search
        rating_el = secici.css_first("span.label-imdb b")
        rating_text = rating_el.text(strip=True) if rating_el else ""
        rating_match = re.search(r"[\d.,]+", rating_text)
        rating = rating_match.group() if rating_match else None

        actors = [a.text(strip=True) for a in secici.css("a[href*='/oyuncu/']") if a.text(strip=True)]

        episodes = []
        for sezon_link_el in secici.css("div#seasons-list a"):
            sezon_link = sezon_link_el.attrs.get("href")
            if not sezon_link:
                continue

            sezon_url    = self.fix_url(sezon_link)
            sezon_istek  = await self.httpx.get(sezon_url)
            sezon_secici = HTMLParser(sezon_istek.text)

            for bolum in sezon_secici.css("article.grid-box"):
                ep_link = bolum.css_first("div.post-title a")
                if not ep_link:
                    continue

                ep_title = ep_link.text(strip=True)
                ep_href  = ep_link.attrs.get("href")

                # re_first yerine re.search
                ep_title_text = ep_title or ""
                season_match  = re.search(r"(\d+)\. ?Sezon", ep_title_text)
                episode_match = re.search(r"(\d+)\. ?Bölüm", ep_title_text)

                ep_season  = season_match.group(1) if season_match else None
                ep_episode = episode_match.group(1) if episode_match else None

                if ep_title and ep_href:
                    episodes.append(Episode(
                        season  = ep_season,
                        episode = ep_episode,
                        title   = ep_title,
                        url     = self.fix_url(ep_href),
                    ))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster) if poster else None,
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
            secici = HTMLParser(istek.text)
            iframe_el = secici.css_first("div#Player iframe")
            iframe = iframe_el.attrs.get("src") if iframe_el else None

            if iframe:
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
            while True:
                await asyncio.sleep(.3)
                with contextlib.suppress(Exception):
                    istek  = await self.httpx.get(iframe_link)

                    if atob_data := re.search(r"unescape\(\"(.*)\"\)", istek.text):
                        decoded_atob = urllib.parse.unquote(atob_data[1])
                        str_atob     = base64.b64decode(decoded_atob).decode("utf-8")

                    iframe_el = HTMLParser(str_atob).css_first("div#Player iframe")
                    if iframe_el:
                        results.append(iframe_el.attrs.get("src"))

                    break

        elif "/player/haydi.php" in iframe_link:
            okru_url = base64.b64decode(iframe_link.split("?v=")[-1]).decode("utf-8")
            results.append(okru_url)

        return results

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)

        results = []
        main_iframe_el = secici.css_first("div#video-area iframe")
        main_iframe = main_iframe_el.attrs.get("src") if main_iframe_el else None

        if main_iframe:
            if decoded := await self._iframe_decode(self.name, main_iframe, url):
                for iframe in decoded:
                    data = await self.extract(iframe)
                    if data:
                        results.append(data)

        for alternatif in secici.css("div.video-toolbar option[value]"):
            alt_name = alternatif.text(strip=True)
            alt_link = alternatif.attrs.get("value")

            if not alt_link:
                continue

            self.httpx.headers.update({"Referer": url})
            alt_istek = await self.httpx.get(alt_link)
            alt_istek.raise_for_status()

            alt_secici = HTMLParser(alt_istek.text)
            alt_iframe_el = alt_secici.css_first("div#video-area iframe")
            alt_iframe = alt_iframe_el.attrs.get("src") if alt_iframe_el else None

            if alt_iframe:
                if decoded := await self._iframe_decode(alt_name, alt_iframe, url):
                    for iframe in decoded:
                        data = await self.extract(iframe, prefix=alt_name)
                        if data:
                            results.append(data)

        return results
