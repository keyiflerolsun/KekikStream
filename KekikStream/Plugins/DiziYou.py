# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, Subtitle, ExtractResult, HTMLHelper

class DiziYou(PluginBase):
    name        = "DiziYou"
    language    = "tr"
    main_url    = "https://www.diziyou.one"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Diziyou en kaliteli Türkçe dublaj ve altyazılı yabancı dizi izleme sitesidir. Güncel ve efsanevi dizileri 1080p Full HD kalitede izlemek için hemen tıkla!"

    main_page   = {
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Aile"                 : "Aile",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Aksiyon"              : "Aksiyon",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Animasyon"            : "Animasyon",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Belgesel"             : "Belgesel",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Bilim+Kurgu"          : "Bilim Kurgu",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Dram"                 : "Dram",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Fantazi"              : "Fantazi",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Gerilim"              : "Gerilim",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Gizem"                : "Gizem",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Komedi"               : "Komedi",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Korku"                : "Korku",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Macera"               : "Macera",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Sava%C5%9F"           : "Savaş",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Su%C3%A7"             : "Suç",
        f"{main_url}/dizi-arsivi/page/SAYFA/?tur=Vah%C5%9Fi+Bat%C4%B1" : "Vahşi Batı"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url.replace('SAYFA', str(page))}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.single-item"):
            title  = secici.select_text("div#categorytitle a", veri)
            href   = secici.select_attr("div#categorytitle a", "href", veri)
            poster = secici.select_attr("img", "src", veri)

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for afis in secici.select("div.incontent div#list-series"):
            title  = secici.select_text("div#categorytitle a", afis)
            href   = secici.select_attr("div#categorytitle a", "href", afis)
            poster = (secici.select_attr("img", "src", afis) or secici.select_attr("img", "data-src", afis))

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

        poster      = secici.select_poster("div.category_image img")
        title       = secici.select_text("h1.title-border")
        description = secici.select_direct_text("div#icerikcatright")
        tags        = secici.select_texts("div.genres a")
        rating      = secici.regex_first(r"(?is)IMDB\s*:\s*</span>([0-9.]+)", secici.html)
        year        = secici.extract_year("div#icerikcat2")
        raw_actors  = secici.meta_value("Oyuncular", container_selector="div#icerikcat2")
        actors      = [x.strip() for x in raw_actors.split(",")] if raw_actors else None

        episodes = []
        for link in secici.select("div#scrollbar-container a"):
            href = secici.select_attr(None, "href", link)
            if href:
                name = secici.select_text("div.bolumismi", link).strip("()")
                s, e = secici.extract_season_episode(f"{name} {href}")
                if e:
                    episodes.append(Episode(
                        season  = s or 1,
                        episode = e,
                        title   = name,
                        url     = self.fix_url(href)
                    ))

        return SeriesInfo(
            url         = url,
            poster      = poster,
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            episodes    = episodes,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        # Player iframe'inden ID'yi yakala
        iframe_src = secici.select_attr("iframe#diziyouPlayer", "src") or secici.select_attr("iframe[src*='/player/']", "src")
        if not iframe_src:
            return []

        item_id      = iframe_src.split("/")[-1].replace(".html", "")
        base_storage = self.main_url.replace("www", "storage")

        subtitles = []
        for sub in [("turkceAltyazili", "tr", "Türkçe"), ("ingilizceAltyazili", "en", "İngilizce")]:
            if secici.select_first(f"span#{sub[0]}"):
                subtitles.append(Subtitle(
                    name = f"{sub[2]} Altyazı",
                    url  = f"{base_storage}/subtitles/{item_id}/{sub[1]}.vtt"
                ))

        results = []
        # Altyazılı Seçenek (Eğer varsa)
        if secici.select_first("span#turkceAltyazili") or secici.select_first("span#ingilizceAltyazili"):
            results.append(ExtractResult(
                name      = "Altyazılı",
                url       = f"{base_storage}/episodes/{item_id}/play.m3u8",
                referer   = url,
                subtitles = subtitles
            ))

        # Dublaj Seçeneği (Eğer varsa)
        if secici.select_first("span#turkceDublaj"):
            results.append(ExtractResult(
                name      = "Türkçe Dublaj",
                url       = f"{base_storage}/episodes/{item_id}_tr/play.m3u8",
                referer   = url,
                subtitles = subtitles
            ))

        return results
