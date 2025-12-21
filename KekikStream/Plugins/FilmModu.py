# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, Subtitle
from parsel import Selector
import re

class FilmModu(PluginBase):
    name        = "FilmModu"
    language    = "tr"
    main_url    = "https://www.filmmodu.ws"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Film modun geldiyse yüksek kalitede yeni filmleri izle, 1080p izleyebileceğiniz reklamsız tek film sitesi."

    main_page   = {
        f"{main_url}/hd-film-kategori/4k-film-izle?page=SAYFA"          : "4K",
        f"{main_url}/hd-film-kategori/aile-filmleri?page=SAYFA"         : "Aile",
        f"{main_url}/hd-film-kategori/aksiyon?page=SAYFA"               : "Aksiyon",
        f"{main_url}/hd-film-kategori/animasyon?page=SAYFA"             : "Animasyon",
        f"{main_url}/hd-film-kategori/belgeseller?page=SAYFA"           : "Belgesel",
        f"{main_url}/hd-film-kategori/bilim-kurgu-filmleri?page=SAYFA"  : "Bilim-Kurgu",
        f"{main_url}/hd-film-kategori/dram-filmleri?page=SAYFA"         : "Dram",
        f"{main_url}/hd-film-kategori/fantastik-filmler?page=SAYFA"     : "Fantastik",
        f"{main_url}/hd-film-kategori/gerilim?page=SAYFA"               : "Gerilim",
        f"{main_url}/hd-film-kategori/gizem-filmleri?page=SAYFA"        : "Gizem",
        f"{main_url}/hd-film-kategori/hd-hint-filmleri?page=SAYFA"      : "Hint Filmleri",
        f"{main_url}/hd-film-kategori/kisa-film?page=SAYFA"             : "Kısa Film",
        f"{main_url}/hd-film-kategori/hd-komedi-filmleri?page=SAYFA"    : "Komedi",
        f"{main_url}/hd-film-kategori/korku-filmleri?page=SAYFA"        : "Korku",
        f"{main_url}/hd-film-kategori/kult-filmler-izle?page=SAYFA"     : "Kült Filmler",
        f"{main_url}/hd-film-kategori/macera-filmleri?page=SAYFA"       : "Macera",
        f"{main_url}/hd-film-kategori/muzik?page=SAYFA"                 : "Müzik",
        f"{main_url}/hd-film-kategori/odullu-filmler-izle?page=SAYFA"   : "Oscar Ödüllü",
        f"{main_url}/hd-film-kategori/romantik-filmler?page=SAYFA"      : "Romantik",
        f"{main_url}/hd-film-kategori/savas?page=SAYFA"                 : "Savaş",
        f"{main_url}/hd-film-kategori/stand-up?page=SAYFA"              : "Stand Up",
        f"{main_url}/hd-film-kategori/suc-filmleri?page=SAYFA"          : "Suç",
        f"{main_url}/hd-film-kategori/tarih?page=SAYFA"                 : "Tarih",
        f"{main_url}/hd-film-kategori/tavsiye-filmler?page=SAYFA"       : "Tavsiye",
        f"{main_url}/hd-film-kategori/tv-film?page=SAYFA"               : "TV Film",
        f"{main_url}/hd-film-kategori/vahsi-bati-filmleri?page=SAYFA"   : "Vahşi Batı",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(url.replace("SAYFA", str(page)))
        secici = Selector(istek.text)

        return [
            MainPageResult(
                category = category,
                title    = veri.css("a::text").get(),
                url      = self.fix_url(veri.css("a::attr(href)").get()),
                poster   = self.fix_url(veri.css("picture img::attr(data-src)").get()),
            )
                for veri in secici.css("div.movie")
                    if veri.css("a::text").get()
        ]

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/film-ara?term={query}")
        secici = Selector(istek.text)

        return [
            SearchResult(
                title  = veri.css("a::text").get(),
                url    = self.fix_url(veri.css("a::attr(href)").get()),
                poster = self.fix_url(veri.css("picture img::attr(data-src)").get()),
            )
                for veri in secici.css("div.movie")
                    if veri.css("a::text").get()
        ]

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        org_title = secici.css("div.titles h1::text").get()
        alt_title = secici.css("div.titles h2::text").get()
        title     = f"{org_title} - {alt_title}" if alt_title else org_title

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(secici.css("img.img-responsive::attr(src)").get()),
            title       = title,
            description = secici.css("p[itemprop='description']::text").get(),
            tags        = [a.css("::text").get() for a in secici.css("a[href*='film-tur/']")],
            year        = secici.css("span[itemprop='dateCreated']::text").get(),
            actors      = [a.css("span::text").get() for a in secici.css("a[itemprop='actor']")],
        )

    async def load_links(self, url: str) -> list[dict]:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        alternates = secici.css("div.alternates a")
        if not alternates:
            return []  # No alternates available

        results = []

        for alternatif in alternates:
            alt_link = self.fix_url(alternatif.css("::attr(href)").get())
            alt_name = alternatif.css("::text").get()

            if alt_name == "Fragman" or not alt_link:
                continue

            alt_istek = await self.httpx.get(alt_link)
            alt_text  = alt_istek.text

            vid_id   = re.search(r"var videoId = '(.*)'", alt_text)
            vid_type = re.search(r"var videoType = '(.*)'", alt_text)

            if not vid_id or not vid_type:
                continue

            source_istek = await self.httpx.get(
                f"{self.main_url}/get-source?movie_id={vid_id[1]}&type={vid_type[1]}"
            )
            source_data = source_istek.json()

            if source_data.get("subtitle"):
                subtitle_url = self.fix_url(source_data["subtitle"])
            else:
                subtitle_url = None

            for source in source_data.get("sources", []):
                results.append({
                    "name"      : f"{self.name} | {alt_name} | {source.get('label', 'Bilinmiyor')}",
                    "url"       : self.fix_url(source["src"]),
                    "referer"   : f"{self.main_url}/",
                    "subtitles" : [Subtitle(name="Türkçe", url=subtitle_url)] if subtitle_url else []
                })

        return results
