# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper

class FilmModu(PluginBase):
    name        = "FilmModu"
    language    = "tr"
    main_url    = "https://www.filmmodu.one"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Film modun geldiyse yüksek kalitede hd film izle, 1080p izleyebileceğiniz reklamsız ve hızlı film sitesi."

    main_page   = {
        f"{main_url}/film-tur/4k-film-izle"         : "4K",
        f"{main_url}/film-tur/aile-filmleri"        : "Aile",
        f"{main_url}/film-tur/aksiyon"              : "Aksiyon",
        f"{main_url}/film-tur/animasyon"            : "Animasyon",
        f"{main_url}/film-tur/belgeseller"          : "Belgesel",
        f"{main_url}/film-tur/bilim-kurgu-filmleri" : "Bilim-Kurgu",
        f"{main_url}/film-tur/dram-filmleri"        : "Dram",
        f"{main_url}/film-tur/fantastik-filmler"    : "Fantastik",
        f"{main_url}/film-tur/gerilim"              : "Gerilim",
        f"{main_url}/film-tur/gizem-filmleri"       : "Gizem",
        f"{main_url}/film-tur/hd-hint-filmleri"     : "Hint Filmleri",
        f"{main_url}/film-tur/kisa-film"            : "Kısa Film",
        f"{main_url}/film-tur/hd-komedi-filmleri"   : "Komedi",
        f"{main_url}/film-tur/korku-filmleri"       : "Korku",
        f"{main_url}/film-tur/kult-filmler-izle"    : "Kült Filmler",
        f"{main_url}/film-tur/macera-filmleri"      : "Macera",
        f"{main_url}/film-tur/muzik"                : "Müzik",
        f"{main_url}/film-tur/odullu-filmler-izle"  : "Oscar Ödüllü",
        f"{main_url}/film-tur/romantik-filmler"     : "Romantik",
        f"{main_url}/film-tur/savas"                : "Savaş",
        f"{main_url}/film-tur/stand-up"             : "Stand Up",
        f"{main_url}/film-tur/suc-filmleri"         : "Suç",
        f"{main_url}/film-tur/tarih"                : "Tarih",
        f"{main_url}/film-tur/tavsiye-filmler"      : "Tavsiye",
        f"{main_url}/film-tur/tv-film"              : "TV Film",
        f"{main_url}/film-tur/vahsi-bati-filmleri"  : "Vahşi Batı",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.async_cf_get(f"{url}?page={page}" if page > 1 else url)
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movie"):
            title  = veri.select_text("a")
            href   = veri.select_attr("a", "href")
            poster = veri.select_attr("picture img", "data-src")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.async_cf_get(f"{self.main_url}/film-ara?term={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movie"):
            title  = veri.select_text("a")
            href   = veri.select_attr("a", "href")
            poster = veri.select_attr("picture img", "data-src")

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.async_cf_get(url)
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
        istek  = await self.async_cf_get(url)
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
            alt_istek = await self.async_cf_get(alt_link)
            secici    = HTMLHelper(alt_istek.text)

            vid_id   = secici.regex_first(r"var videoId = '([^']*)'")
            vid_type = secici.regex_first(r"var videoType = '([^']*)'")

            if not vid_id or not vid_type:
                continue

            source_istek = await self.async_cf_get(f"{self.main_url}/get-source?movie_id={vid_id}&type={vid_type}")
            source_data  = source_istek.json()

            if source_data.get("subtitle"):
                subtitle_url = self.fix_url(source_data["subtitle"])
            else:
                subtitle_url = None

            for source in source_data.get("sources", []):
                results.append(ExtractResult(
                    name      = f"{alt_name} | {source.get('label', 'Bilinmiyor')}",
                    url       = self.fix_url(source["src"]),
                    referer   = f"{self.main_url}/",
                    subtitles = [self.new_subtitle(subtitle_url, "Türkçe")] if subtitle_url else []
                ))

        return results
