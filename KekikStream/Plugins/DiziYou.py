# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, Subtitle, ExtractResult
from parsel           import Selector
import re

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
        secici = Selector(istek.text)

        return [
            MainPageResult(
                category = category,
                title    = veri.css("div#categorytitle a::text").get(),
                url      = self.fix_url(veri.css("div#categorytitle a::attr(href)").get()),
                poster   = self.fix_url(veri.css("img::attr(src)").get()),
            )
                for veri in secici.css("div.single-item")
        ]

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = Selector(istek.text)

        return [
            SearchResult(
                title  = afis.css("div#categorytitle a::text").get().strip(),
                url    = self.fix_url(afis.css("div#categorytitle a::attr(href)").get()),
                poster = self.fix_url(afis.css("img::attr(src)").get() or afis.css("img::attr(data-src)").get())
            )
                for afis in secici.css("div.incontent div#list-series")
        ]

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        # Title - div.title h1 içinde
        title_raw   = secici.css("div.title h1::text").get()
        title       = title_raw.strip() if title_raw else ""
        
        # Fallback: Eğer title boşsa URL'den çıkar (telif kısıtlaması olan sayfalar için)
        if not title:
            # URL'den slug'ı al: https://www.diziyou.one/jasmine/ -> jasmine -> Jasmine
            slug = url.rstrip('/').split('/')[-1]
            title = slug.replace('-', ' ').title()
        
        # Poster
        poster_raw  = secici.css("div.category_image img::attr(src)").get()
        poster      = self.fix_url(poster_raw) if poster_raw else ""
        year        = secici.xpath("//span[contains(., 'Yapım Yılı')]/following-sibling::text()[1]").get()
        description = secici.css("div.diziyou_desc::text").get()
        if description:
            description = description.strip()
        tags        = secici.css("div.genres a::text").getall()
        rating      = secici.xpath("//span[contains(., 'IMDB')]/following-sibling::text()[1]").get()
        _actors     = secici.xpath("//span[contains(., 'Oyuncular')]/following-sibling::text()[1]").get()
        actors      = [actor.strip() for actor in _actors.split(",")] if _actors else []

        episodes    = []
        # Episodes - bolumust her bölüm için bir <a> içinde
        # :has() parsel'de çalışmıyor, XPath kullanıyoruz
        for link in secici.xpath('//a[div[@class="bolumust"]]'):
            ep_name_raw = link.css("div.baslik::text").get()
            if not ep_name_raw:
                continue
            ep_name = ep_name_raw.strip()
            
            ep_href = self.fix_url(link.css("::attr(href)").get())
            if not ep_href:
                continue

            # Bölüm ismi varsa al
            ep_name_raw_clean = link.css("div.bolumismi::text").get()
            ep_name_clean = ep_name_raw_clean.strip().replace("(", "").replace(")", "").strip() if ep_name_raw_clean else ep_name

            ep_episode = re.search(r"(\d+)\. Bölüm", ep_name)[1]
            ep_season  = re.search(r"(\d+)\. Sezon", ep_name)[1]

            episode = Episode(
                season  = ep_season,
                episode = ep_episode,
                title   = ep_name_clean,
                url     = ep_href,
            )

            episodes.append(episode)

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

    async def load_links(self, url: str) -> list[dict]:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        # Title ve episode name - None kontrolü ekle
        item_title_raw = secici.css("div.title h1::text").get()
        item_title = item_title_raw.strip() if item_title_raw else ""
        
        ep_name_raw = secici.css("div#bolum-ismi::text").get()
        ep_name = ep_name_raw.strip() if ep_name_raw else ""
        
        # Player src'den item_id çıkar
        player_src = secici.css("iframe#diziyouPlayer::attr(src)").get()
        if not player_src:
            return []  # Player bulunamadıysa boş liste döndür
        
        item_id = player_src.split("/")[-1].replace(".html", "")

        subtitles   = []
        stream_urls = []

        for secenek in secici.css("span.diziyouOption"):
            opt_id  = secenek.css("::attr(id)").get()
            op_name = secenek.css("::text").get()

            match opt_id:
                case "turkceAltyazili":
                    subtitles.append(Subtitle(
                        name = op_name,
                        url  = self.fix_url(f"{self.main_url.replace('www', 'storage')}/subtitles/{item_id}/tr.vtt"),
                    ))
                    veri = {
                        "dil": "Orjinal Dil (TR Altyazı)",
                        "url": f"{self.main_url.replace('www', 'storage')}/episodes/{item_id}/play.m3u8"
                    }
                    if veri not in stream_urls:
                        stream_urls.append(veri)
                case "ingilizceAltyazili":
                    subtitles.append(Subtitle(
                        name = op_name,
                        url  = self.fix_url(f"{self.main_url.replace('www', 'storage')}/subtitles/{item_id}/en.vtt"),
                    ))
                    veri = {
                        "dil": "Orjinal Dil (EN Altyazı)",
                        "url": f"{self.main_url.replace('www', 'storage')}/episodes/{item_id}/play.m3u8"
                    }
                    if veri not in stream_urls:
                        stream_urls.append(veri)
                case "turkceDublaj":
                    stream_urls.append({
                        "dil": "Türkçe Dublaj",
                        "url": f"{self.main_url.replace('www', 'storage')}/episodes/{item_id}_tr/play.m3u8"
                    })

        results = []
        for stream in stream_urls:
            results.append({
                "url"       : stream.get("url"),
                "name"      : f"{stream.get('dil')}",
                "referer"   : url,
                "subtitles" : subtitles
            })

        return results

    async def play(self, **kwargs):
        extract_result = ExtractResult(**kwargs)
        self.media_handler.title = kwargs.get("name")
        if self.name not in self.media_handler.title:
            self.media_handler.title = f"{self.name} | {self.media_handler.title}"

        self.media_handler.play_media(extract_result)