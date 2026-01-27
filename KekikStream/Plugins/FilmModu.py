# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, Subtitle, ExtractResult, HTMLHelper

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
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movie"):
            title  = secici.select_text("a", veri)
            href   = secici.select_attr("a", "href", veri)
            poster = secici.select_attr("picture img", "data-src", veri)

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/film-ara?term={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movie"):
            title  = secici.select_text("a", veri)
            href   = secici.select_attr("a", "href", veri)
            poster = secici.select_attr("picture img", "data-src", veri)

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        org_title   = secici.select_text("div.titles h1")
        alt_title   = secici.select_text("div.titles h2")
        title       = f"{org_title} - {alt_title}" if alt_title else (org_title)
        poster      = secici.select_poster("img.img-responsive")
        description = secici.select_text("p[itemprop='description']")
        tags        = secici.select_texts("a[href*='film-tur/']")
        rating      = secici.meta_value("IMDB")
        year        = secici.extract_year("span[itemprop='dateCreated']")
        actors      = secici.select_texts("a[itemprop='actor'] span")

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        alternates = secici.select("div.alternates a")
        if not alternates:
            return []

        results = []

        for alternatif in alternates:
            alt_link = alternatif.attrs.get("href")
            alt_name = alternatif.text(strip=True)

            if alt_name == "Fragman" or not alt_link:
                continue

            alt_link  = self.fix_url(alt_link)
            alt_istek = await self.httpx.get(alt_link)
            secici    = HTMLHelper(alt_istek.text)

            vid_id   = secici.regex_first(r"var videoId = '([^']*)'")
            vid_type = secici.regex_first(r"var videoType = '([^']*)'")

            if not vid_id or not vid_type:
                continue

            source_istek = await self.httpx.get(f"{self.main_url}/get-source?movie_id={vid_id}&type={vid_type}")
            source_data  = source_istek.json()

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
