# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, Subtitle, ExtractResult
from selectolax.parser import HTMLParser
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
        secici = HTMLParser(istek.text)

        results = []
        for veri in secici.css("div.movie"):
            link_el = veri.css_first("a")
            img_el  = veri.css_first("picture img")

            title  = link_el.text(strip=True) if link_el else None
            href   = link_el.attrs.get("href") if link_el else None
            poster = img_el.attrs.get("data-src") if img_el else None

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster) if poster else None,
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/film-ara?term={query}")
        secici = HTMLParser(istek.text)

        results = []
        for veri in secici.css("div.movie"):
            link_el = veri.css_first("a")
            img_el  = veri.css_first("picture img")

            title  = link_el.text(strip=True) if link_el else None
            href   = link_el.attrs.get("href") if link_el else None
            poster = img_el.attrs.get("data-src") if img_el else None

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster) if poster else None,
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)

        org_title_el = secici.css_first("div.titles h1")
        alt_title_el = secici.css_first("div.titles h2")

        org_title = org_title_el.text(strip=True) if org_title_el else ""
        alt_title = alt_title_el.text(strip=True) if alt_title_el else ""
        title     = f"{org_title} - {alt_title}" if alt_title else org_title

        poster_el = secici.css_first("img.img-responsive")
        poster    = poster_el.attrs.get("src") if poster_el else None

        desc_el     = secici.css_first("p[itemprop='description']")
        description = desc_el.text(strip=True) if desc_el else None

        tags = [a.text(strip=True) for a in secici.css("a[href*='film-tur/']") if a.text(strip=True)]

        year_el = secici.css_first("span[itemprop='dateCreated']")
        year    = year_el.text(strip=True) if year_el else None

        actors = []
        for a in secici.css("a[itemprop='actor']"):
            span_el = a.css_first("span")
            if span_el and span_el.text(strip=True):
                actors.append(span_el.text(strip=True))

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster) if poster else None,
            title       = title,
            description = description,
            tags        = tags,
            year        = year,
            actors      = actors,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)

        alternates = secici.css("div.alternates a")
        if not alternates:
            return []

        results = []

        for alternatif in alternates:
            alt_link = alternatif.attrs.get("href")
            alt_name = alternatif.text(strip=True)

            if alt_name == "Fragman" or not alt_link:
                continue

            alt_link = self.fix_url(alt_link)
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
                results.append(ExtractResult(
                    name      = f"{self.name} | {alt_name} | {source.get('label', 'Bilinmiyor')}",
                    url       = self.fix_url(source["src"]),
                    referer   = f"{self.main_url}/",
                    subtitles = [Subtitle(name="Türkçe", url=subtitle_url)] if subtitle_url else []
                ))

        return results
