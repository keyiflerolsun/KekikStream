# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, ExtractResult, HTMLHelper
from json             import dumps, loads
import re

class FilmEkseni(PluginBase):
    name        = "FilmEkseni"
    language    = "tr"
    main_url    = "https://filmekseni.cc"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Film Ekseni ⚡️ Vizyonda ki, en güncel ve en yeni filmleri full hd kalitesinde türkçe dublaj ve altyazı seçenekleriyle 1080p olarak izleyebileceğiniz adresiniz."

    main_page = {
        f"{main_url}/tur/aile-filmleri/page"        : "Aile Filmleri",
        f"{main_url}/tur/aksiyon-filmleri/page"     : "Aksiyon Filmleri",
        f"{main_url}/tur/animasyon-film-izle/page"  : "Animasyon Filmleri",
        f"{main_url}/tur/bilim-kurgu-filmleri/page" : "Bilim Kurgu Filmleri",
        f"{main_url}/tur/biyografi-filmleri/page"   : "Biyografi Filmleri",
        f"{main_url}/tur/dram-filmleri-izle/page"   : "Dram Filmleri",
        f"{main_url}/tur/fantastik-filmler/page"    : "Fantastik Filmleri",
        f"{main_url}/tur/gerilim-filmleri/page"     : "Gerilim Filmleri",
        f"{main_url}/tur/gizem-filmleri/page"       : "Gizem Filmleri",
        f"{main_url}/tur/komedi-filmleri/page"      : "Komedi Filmleri",
        f"{main_url}/tur/korku-filmleri/page"       : "Korku Filmleri",
        f"{main_url}/tur/macera-filmleri/page"      : "Macera Filmleri",
        f"{main_url}/tur/romantik-filmler/page"     : "Romantik Filmleri",
        f"{main_url}/tur/savas-filmleri/page"       : "Savaş Filmleri",
        f"{main_url}/tur/suc-filmleri/page"         : "Suç Filmleri",
        f"{main_url}/tur/tarih-filmleri/page"       : "Tarih Filmleri",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek   = await self.httpx.get(f"{url}/{page}/")
        helper  = HTMLHelper(istek.text)
        posters = helper.select("div.poster")

        return [
            MainPageResult(
                category = category,
                title    = self.clean_title(helper.select_text("h2", veri)),
                url      = helper.select_attr("a", "href", veri),
                poster   = helper.select_attr("img", "data-src", veri)
            )
            for veri in posters
        ]

    async def search(self, query: str) -> list[SearchResult]:
        url = f"{self.main_url}/search/"
        headers = {
            "X-Requested-With" : "XMLHttpRequest",
            "Content-Type"     : "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer"          : self.main_url,
        }
        data = {"query": query}
        
        istek = await self.httpx.post(url, headers=headers, data=data)
        veriler = istek.json().get("result", [])

        return [
            SearchResult(
                title  = veri.get("title"),
                url    = f"{self.main_url}/{veri.get('slug')}",
                poster = f"{self.main_url}/uploads/poster/{veri.get('cover')}" if veri.get('cover') else None,
            )
            for veri in veriler
        ]

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        helper = HTMLHelper(istek.text)

        title       = self.clean_title(helper.select_text("div.page-title h1"))
        poster      = helper.select_poster("picture.poster-auto img")
        description = helper.select_direct_text("article.text-white p")
        year        = helper.extract_year("div.page-title", "strong a")
        tags        = helper.select_texts("div.pb-2 a[href*='/tur/']")
        rating      = helper.select_text("div.rate")
        duration    = helper.regex_first(r"(\d+)", helper.select_text("div.d-flex.flex-column.text-nowrap"))
        actors      = helper.select_texts("div.card-body.p-0.pt-2 .story-item .story-item-title")

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster) if poster else None,
            title       = title or "Bilinmiyor",
            description = description,
            tags        = tags,
            rating      = rating,
            year        = str(year) if year else None,
            actors      = actors if actors else None,
            duration    = int(duration) if duration else None
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        helper = HTMLHelper(istek.text)
        
        iframe = helper.select_first("div.card-video iframe")
        if not iframe:
            return []
            
        iframe_url = iframe.attrs.get("data-src") or iframe.attrs.get("src")
        if not iframe_url:
            return []
            
        if iframe_url.startswith("//"):
            iframe_url = f"https:{iframe_url}"
            
        video_id = iframe_url.split("/")[-1]
        master_url = f"https://eksenload.site/uploads/encode/{video_id}/master.m3u8"
        
        results = [
            ExtractResult(
                url     = master_url,
                name    = f"{self.name} | 1080p",
                referer = self.main_url
            )
        ]
        
        return results
