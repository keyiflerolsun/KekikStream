# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, Subtitle
from parsel import Selector
import re

class DiziPal(PluginBase):
    name        = "DiziPal"
    language    = "tr"
    main_url    = "https://dizipal1222.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Yabancı Dizi ve Film izle."

    main_page   = {
        f"{main_url}/diziler/son-bolumler"              : "Son Bölümler",
        f"{main_url}/diziler"                           : "Yeni Diziler",
        f"{main_url}/filmler"                           : "Yeni Filmler",
        f"{main_url}/koleksiyon/netflix"                : "Netflix",
        f"{main_url}/koleksiyon/exxen"                  : "Exxen",
        f"{main_url}/koleksiyon/blutv"                  : "BluTV",
        f"{main_url}/koleksiyon/disney"                 : "Disney+",
        f"{main_url}/koleksiyon/amazon-prime"           : "Amazon Prime",
        f"{main_url}/koleksiyon/tod-bein"               : "TOD (beIN)",
        f"{main_url}/koleksiyon/gain"                   : "Gain",
        f"{main_url}/tur/mubi"                          : "Mubi",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.cffi.get(url)
        secici = Selector(istek.text)

        results = []

        if "/son-bolumler" in url:
            for veri in secici.css("div.episode-item"):
                name     = veri.css("div.name::text").get()
                episode  = veri.css("div.episode::text").get()
                href     = veri.css("a::attr(href)").get()
                poster   = veri.css("img::attr(src)").get()

                if name and href:
                    ep_text = episode.strip().replace(". Sezon ", "x").replace(". Bölüm", "") if episode else ""
                    title   = f"{name} {ep_text}"
                    # Son bölümler linkini dizi sayfasına çevir
                    dizi_url = href.split("/sezon")[0] if "/sezon" in href else href

                    results.append(MainPageResult(
                        category = category,
                        title    = title,
                        url      = self.fix_url(dizi_url),
                        poster   = self.fix_url(poster) if poster else None,
                    ))
        else:
            for veri in secici.css("article.type2 ul li"):
                title  = veri.css("span.title::text").get()
                href   = veri.css("a::attr(href)").get()
                poster = veri.css("img::attr(src)").get()

                if title and href:
                    results.append(MainPageResult(
                        category = category,
                        title    = title,
                        url      = self.fix_url(href),
                        poster   = self.fix_url(poster) if poster else None,
                    ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        self.cffi.headers.update({
            "Accept"           : "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With" : "XMLHttpRequest"
        })

        istek = await self.cffi.post(
            url  = f"{self.main_url}/api/search-autocomplete",
            data = {"query": query}
        )

        try:
            data = istek.json()
        except Exception:
            return []

        results = []

        # API bazen dict, bazen list döner
        items = data.values() if isinstance(data, dict) else data

        for item in items:
            if not isinstance(item, dict):
                continue

            title  = item.get("title")
            url    = item.get("url")
            poster = item.get("poster")

            if title and url:
                results.append(SearchResult(
                    title  = title,
                    url    = f"{self.main_url}{url}",
                    poster = self.fix_url(poster) if poster else None,
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        # Reset headers to get HTML response
        self.cffi.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })
        self.cffi.headers.pop("X-Requested-With", None)

        istek  = await self.cffi.get(url)
        secici = Selector(text=istek.text, type="html")

        poster      = self.fix_url(secici.css("meta[property='og:image']::attr(content)").get())
        year        = secici.xpath("//div[text()='Yapım Yılı']//following-sibling::div/text()").get()
        description = secici.css("div.summary p::text").get()
        rating      = secici.xpath("//div[text()='IMDB Puanı']//following-sibling::div/text()").get()
        tags_raw    = secici.xpath("//div[text()='Türler']//following-sibling::div/text()").get()
        tags        = [t.strip() for t in tags_raw.split() if t.strip()] if tags_raw else None

        dur_text    = secici.xpath("//div[text()='Ortalama Süre']//following-sibling::div/text()").get()
        dur_match   = re.search(r"(\d+)", dur_text or "")
        duration    = int(dur_match[1]) if dur_match else None

        if "/dizi/" in url:
            title = secici.css("div.cover h5::text").get()

            episodes = []
            for ep in secici.css("div.episode-item"):
                ep_name    = ep.css("div.name::text").get()
                ep_href    = ep.css("a::attr(href)").get()
                ep_text    = ep.css("div.episode::text").get() or ""
                ep_parts   = ep_text.strip().split(" ")

                ep_season  = None
                ep_episode = None
                if len(ep_parts) >= 4:
                    try:
                        ep_season  = int(ep_parts[0].replace(".", ""))
                        ep_episode = int(ep_parts[2].replace(".", ""))
                    except ValueError:
                        pass

                if ep_name and ep_href:
                    episodes.append(Episode(
                        season  = ep_season,
                        episode = ep_episode,
                        title   = ep_name.strip(),
                        url     = self.fix_url(ep_href),
                    ))

            return SeriesInfo(
                url         = url,
                poster      = poster,
                title       = title,
                description = description.strip() if description else None,
                tags        = tags,
                rating      = rating.strip() if rating else None,
                year        = year.strip() if year else None,
                duration    = duration,
                episodes    = episodes if episodes else None,
            )
        else:
            title = secici.xpath("//div[@class='g-title'][2]/div/text()").get()

            return MovieInfo(
                url         = url,
                poster      = poster,
                title       = title.strip() if title else None,
                description = description.strip() if description else None,
                tags        = tags,
                rating      = rating.strip() if rating else None,
                year        = year.strip() if year else None,
                duration    = duration,
            )

    async def load_links(self, url: str) -> list[dict]:
        # Reset headers to get HTML response
        self.cffi.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })
        self.cffi.headers.pop("X-Requested-With", None)

        istek  = await self.cffi.get(url)
        secici = Selector(istek.text)

        iframe = secici.css(".series-player-container iframe::attr(src)").get()
        if not iframe:
            iframe = secici.css("div#vast_new iframe::attr(src)").get()

        if not iframe:
            return []

        results = []

        self.cffi.headers.update({"Referer": f"{self.main_url}/"})
        i_istek = await self.cffi.get(iframe)
        i_text  = i_istek.text

        # m3u link çıkar
        m3u_match = re.search(r'file:"([^"]+)"', i_text)
        if m3u_match:
            m3u_link = m3u_match[1]

            # Altyazıları çıkar
            subtitles = []
            sub_match = re.search(r'"subtitle":"([^"]+)"', i_text)
            if sub_match:
                sub_text = sub_match[1]
                if "," in sub_text:
                    for sub in sub_text.split(","):
                        lang = sub.split("[")[1].split("]")[0] if "[" in sub else "Türkçe"
                        sub_url = sub.replace(f"[{lang}]", "")
                        subtitles.append(Subtitle(name=lang, url=self.fix_url(sub_url)))
                else:
                    lang = sub_text.split("[")[1].split("]")[0] if "[" in sub_text else "Türkçe"
                    sub_url = sub_text.replace(f"[{lang}]", "")
                    subtitles.append(Subtitle(name=lang, url=self.fix_url(sub_url)))

            results.append({
                "name"      : self.name,
                "url"       : m3u_link,
                "referer"   : f"{self.main_url}/",
                "subtitles" : subtitles
            })
        else:
            # Extractor'a yönlendir
            extractor = self.ex_manager.find_extractor(iframe)
            results.append({
                "name"    : f"{extractor.name if extractor else self.name}",
                "url"     : iframe,
                "referer" : f"{self.main_url}/",
            })

        return results

    async def play(self, name: str, url: str, referer: str, subtitles: list[Subtitle]):
        extract_result = ExtractResult(name=name, url=url, referer=referer, subtitles=subtitles)
        self.media_handler.title = name
        if self.name not in self.media_handler.title:
            self.media_handler.title = f"{self.name} | {self.media_handler.title}"

        self.media_handler.play_media(extract_result)
