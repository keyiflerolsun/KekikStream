# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import kekik_cache, PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, Subtitle, ExtractResult
from parsel           import Selector
import re

class DiziYou(PluginBase):
    name        = "DiziYou"
    language    = "tr"
    main_url    = "https://www.diziyou2.com"
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

    _data = {}

    @kekik_cache(ttl=60*60)
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

    @kekik_cache(ttl=60*60)
    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = Selector(istek.text)

        return [
            SearchResult(
                title  = afis.css("div#categorytitle a::text").get().strip(),
                url    = self.fix_url(afis.css("div#categorytitle a::attr(href)").get()),
                poster = self.fix_url(afis.css("img::attr(src)").get()),
            )
                for afis in secici.css("div.incontent div#list-series")
        ]

    @kekik_cache(ttl=60*60)
    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        title       = secici.css("h1::text").get().strip()
        poster      = self.fix_url(secici.css("div.category_image img::attr(src)").get().strip())
        year        = secici.xpath("//span[contains(., 'Yapım Yılı')]/following-sibling::text()[1]").get()
        description = secici.css("div.diziyou_desc::text").get().strip()
        tags        = secici.css("div.genres a::text").getall()
        rating      = secici.xpath("//span[contains(., 'IMDB')]/following-sibling::text()[1]").get()
        _actors     = secici.xpath("//span[contains(., 'Oyuncular')]/following-sibling::text()[1]").get()
        actors      = [actor.strip() for actor in _actors.split(",")] if _actors else []

        episodes    = []
        for it in secici.css("div.bolumust"):
            ep_name = it.css("div.baslik::text").get().strip()
            ep_href = it.xpath("ancestor::a/@href").get()
            if not ep_name or not ep_href:
                continue

            ep_name_clean = it.css("div.bolumismi::text").get().strip().replace("(", "").replace(")", "").strip() if it.css("div.bolumismi::text").get() else ep_name

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

    @kekik_cache(ttl=15*60)
    async def load_links(self, url: str) -> list[str]:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        item_title = secici.css("div.title h1::text").get()
        ep_name    = secici.css("div#bolum-ismi::text").get().strip()
        item_id    = secici.css("iframe#diziyouPlayer::attr(src)").get().split("/")[-1].replace(".html", "")

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
                        "dil": "Orjinal Dil",
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
                        "dil": "Orjinal Dil",
                        "url": f"{self.main_url.replace('www', 'storage')}/episodes/{item_id}/play.m3u8"
                    }
                    if veri not in stream_urls:
                        stream_urls.append(veri)
                case "turkceDublaj":
                    stream_urls.append({
                        "dil": "Dublaj",
                        "url": f"{self.main_url.replace('www', 'storage')}/episodes/{item_id}_tr/play.m3u8"
                    })


        for stream in stream_urls:
            self._data[stream.get("url")] = {
                "ext_name"  : f"{self.name} | {stream.get('dil')}",
                "name"      : f"{self.name} | {stream.get('dil')} | {item_title} - {ep_name}",
                "referer"   : url,
                "headers"   : self.media_handler.headers,
                "subtitles" : subtitles
            }

        return [stream.get("url") for stream in stream_urls]

    async def play(self, name: str, url: str, referer: str, subtitles: list[Subtitle]):
        extract_result = ExtractResult(name=name, url=url, referer=referer, subtitles=subtitles)
        self.media_handler.title = name
        if self.name not in self.media_handler.title:
            self.media_handler.title = f"{self.name} | {self.media_handler.title}"

        self.media_handler.play_media(extract_result)