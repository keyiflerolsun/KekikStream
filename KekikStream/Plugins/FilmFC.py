# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper
import re

class FilmFC(PluginBase):
    name        = "FilmFC"
    language    = "tr"
    main_url    = "https://www.filmfc.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "FilmFC, en yeni erotik filmleri Full HD kalitesinde sunan bir platformdur."

    main_page   = {
        f"{main_url}"                                       : "En Yeniler",
        f"{main_url}/erotikfilmler/abd-erotik"              : "ABD",
        f"{main_url}/erotikfilmler/alman-erotik"            : "Alman",
        f"{main_url}/erotikfilmler/erotik-filmler"          : "Erotik Filmler",
        f"{main_url}/erotikfilmler/fransiz-erotik"          : "Fransız",
        f"{main_url}/erotikfilmler/hint-erotik"             : "Hint",
        f"{main_url}/erotikfilmler/ispanyol-erotik"         : "İspanyol",
        f"{main_url}/erotikfilmler/italyan-erotik"          : "İtalyan",
        f"{main_url}/erotikfilmler/japon-erotik"            : "Japon",
        f"{main_url}/erotikfilmler/konulu-erotik"           : "Konulu",
        f"{main_url}/erotikfilmler/kore-erotik"             : "Kore",
        f"{main_url}/erotikfilmler/lezbiyen-erotik"         : "Lezbiyen",
        f"{main_url}/erotikfilmler/olgun-erotik"            : "Olgun",
        f"{main_url}/erotikfilmler/rus-erotik"              : "Rus",
        f"{main_url}/erotikfilmler/turkce-altyazili-erotik" : "Türkçe Altyazılı",
        f"{main_url}/erotikfilmler/turkce-dublaj-erotik"    : "Türkçe Dublaj",
        f"{main_url}/erotikfilmler/yabanci-erotik"          : "Yabancı",
        f"{main_url}/erotikfilmler/yerli-filmler"           : "Yerli Filmler",
        f"{main_url}/erotikfilmler/yesilcam-erotik"         : "Yeşilçam",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        full_url = f"{url}/page/{page}/" if page > 1 else url
        istek    = await self.async_cf_get(full_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.frag-k"):
            title  = item.select_attr("a.baslik", "title") or item.select_text("a.baslik")
            href   = item.select_attr("a.baslik", "href")
            poster = item.select_attr("img", "src") or item.select_attr("img", "data-src")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title.strip().replace(" izle", ""),
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.async_cf_get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.frag-k"):
            title  = item.select_attr("a.baslik", "title") or item.select_text("a.baslik")
            href   = item.select_attr("a.baslik", "href")
            poster = item.select_attr("img", "src") or item.select_attr("img", "data-src")

            if title and href:
                results.append(SearchResult(
                    title  = title.strip().replace(" izle", ""),
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))
        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        title = secici.select_text("h2") or secici.select_text("title") or ""
        title = title.split("|")[0].split("-")[0].replace(" izle", "").strip()

        poster = secici.select_attr("meta[property='og:image']", "content") or secici.select_attr("link[rel='image_src']", "href")

        description = secici.select_attr("meta[name='description']", "content") or secici.select_attr("meta[property='og:description']", "content")

        duration = None
        tags     = []
        year     = None
        for p in secici.select("p"):
            p_text = p.text(strip=True)
            if p_text.startswith("Süre:"):
                dur_match = re.search(r"(\d+)", p_text)
                if dur_match:
                    duration = int(dur_match.group(1))
            elif p_text.startswith("Tür:"):
                tags_part = p_text.replace("Tür:", "").strip()
                tags      = [t.strip() for t in tags_part.split(",") if t.strip()]
            elif re.match(r"^(19|20)\d{2}$", p_text):
                year = p_text

        rating = secici.select_text("div.puan") or None


        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster) if poster else None,
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            duration    = duration,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        response   = []
        tried_urls = set()

        # Span#plyg içindeki iframe'i önceliklendir
        for iframe in secici.select("span#plyg iframe"):
            src = iframe.attrs.get("src")
            if src:
                src_fixed = self.fix_url(src)
                if src_fixed not in tried_urls:
                    tried_urls.add(src_fixed)
                    data = await self.extract(src_fixed, referer=url)
                    self.collect_results(response, data)

        # Diğer iframeler
        if not response:
            for iframe in secici.select("iframe"):
                src = iframe.attrs.get("src")
                if not src or any(x in src for x in ["youtube", "google", "facebook", "twitter"]):
                    continue

                src_fixed = self.fix_url(src)
                if src_fixed not in tried_urls:
                    tried_urls.add(src_fixed)
                    data = await self.extract(src_fixed, referer=url)
                    self.collect_results(response, data)

        return response
