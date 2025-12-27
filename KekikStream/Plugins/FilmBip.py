# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult
from selectolax.parser import HTMLParser
import re

class FilmBip(PluginBase):
    name        = "FilmBip"
    language    = "tr"
    main_url    = "https://filmbip.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "FilmBip adlı film sitemizde Full HD film izle. Yerli ve yabancı filmleri Türkçe dublaj veya altyazılı şekilde 1080p yüksek kalite film izle"

    main_page   = {
        f"{main_url}/filmler/SAYFA"                 : "Yeni Filmler",
        f"{main_url}/film/tur/aile/SAYFA"           : "Aile",
        f"{main_url}/film/tur/aksiyon/SAYFA"        : "Aksiyon",
        f"{main_url}/film/tur/belgesel/SAYFA"       : "Belgesel",
        f"{main_url}/film/tur/bilim-kurgu/SAYFA"    : "Bilim Kurgu",
        f"{main_url}/film/tur/dram/SAYFA"           : "Dram",
        f"{main_url}/film/tur/fantastik/SAYFA"      : "Fantastik",
        f"{main_url}/film/tur/gerilim/SAYFA"        : "Gerilim",
        f"{main_url}/film/tur/gizem/SAYFA"          : "Gizem",
        f"{main_url}/film/tur/komedi/SAYFA"         : "Komedi",
        f"{main_url}/film/tur/korku/SAYFA"          : "Korku",
        f"{main_url}/film/tur/macera/SAYFA"         : "Macera",
        f"{main_url}/film/tur/muzik/SAYFA"          : "Müzik",
        f"{main_url}/film/tur/romantik/SAYFA"       : "Romantik",
        f"{main_url}/film/tur/savas/SAYFA"          : "Savaş",
        f"{main_url}/film/tur/suc/SAYFA"            : "Suç",
        f"{main_url}/film/tur/tarih/SAYFA"          : "Tarih",
        f"{main_url}/film/tur/vahsi-bati/SAYFA"     : "Western",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        page_url = url.replace("SAYFA", "") if page == 1 else url.replace("SAYFA", str(page))
        page_url = page_url.rstrip("/")

        istek  = await self.httpx.get(page_url)
        secici = HTMLParser(istek.text)

        results = []
        for veri in secici.css("div.poster-long"):
            img = veri.css_first("a.block img.lazy")
            link_el = veri.css_first("a.block")

            title  = img.attrs.get("alt") if img else None
            href   = link_el.attrs.get("href") if link_el else None
            poster = (img.attrs.get("data-src") or img.attrs.get("src")) if img else None

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster) if poster else None,
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek = await self.httpx.post(
            url     = f"{self.main_url}/search",
            headers = {
                "Accept"           : "application/json, text/javascript, */*; q=0.01",
                "X-Requested-With" : "XMLHttpRequest",
                "Content-Type"     : "application/x-www-form-urlencoded; charset=UTF-8",
                "Origin"           : self.main_url,
                "Referer"          : f"{self.main_url}/"
            },
            data    = {"query": query}
        )

        try:
            json_data = istek.json()
            if not json_data.get("success"):
                return []

            html_content = json_data.get("theme", "")
        except Exception:
            return []

        secici = HTMLParser(html_content)

        results = []
        for veri in secici.css("li"):
            link_el = veri.css_first("a.block.truncate")
            href_el = veri.css_first("a")
            img_el  = veri.css_first("img.lazy")

            title  = link_el.text(strip=True) if link_el else None
            href   = href_el.attrs.get("href") if href_el else None
            poster = img_el.attrs.get("data-src") if img_el else None

            if title and href:
                results.append(SearchResult(
                    title  = title.strip(),
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster) if poster else None,
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)
        html_text = istek.text

        title_el = secici.css_first("div.page-title h1")
        title    = title_el.text(strip=True) if title_el else ""

        og_image = secici.css_first("meta[property='og:image']")
        poster   = og_image.attrs.get("content") if og_image else None

        trailer_el = secici.css_first("div.series-profile-trailer")
        trailer    = trailer_el.attrs.get("data-yt") if trailer_el else None

        desc_el = secici.css_first("div.series-profile-infos-in.article p")
        if not desc_el:
            desc_el = secici.css_first("div.series-profile-summary p")
        description = desc_el.text(strip=True) if desc_el else None
        
        tags = [a.text(strip=True) for a in secici.css("div.series-profile-type.tv-show-profile-type a") if a.text(strip=True)]

        # XPath yerine regex kullanarak yıl, süre vs. çıkarma
        year = None
        year_match = re.search(r'Yapım yılı.*?<p[^>]*>(\d{4})</p>', html_text, re.IGNORECASE | re.DOTALL)
        if year_match:
            year = year_match.group(1)

        duration = None
        duration_match = re.search(r'Süre.*?<p[^>]*>(\d+)', html_text, re.IGNORECASE | re.DOTALL)
        if duration_match:
            duration = duration_match.group(1)

        rating = None
        rating_match = re.search(r'IMDB Puanı.*?<span[^>]*>([0-9.]+)</span>', html_text, re.IGNORECASE | re.DOTALL)
        if rating_match:
            rating = rating_match.group(1)

        actors = [img.attrs.get("alt") for img in secici.css("div.series-profile-cast ul li a img") if img.attrs.get("alt")]

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster) if poster else None,
            title       = self.clean_title(title) if title else "",
            description = description,
            tags        = tags,
            year        = year,
            rating      = rating,
            duration    = int(duration) if duration else None,
            actors      = actors,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)

        results = []

        for player in secici.css("div#tv-spoox2"):
            iframe_el = player.css_first("iframe")
            iframe    = iframe_el.attrs.get("src") if iframe_el else None

            if iframe:
                iframe = self.fix_url(iframe)
                data = await self.extract(iframe)
                if data:
                    results.append(data)

        return results
