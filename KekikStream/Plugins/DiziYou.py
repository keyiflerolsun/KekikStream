# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, SearchResult, SeriesInfo, Episode, Subtitle, ExtractResult
from parsel           import Selector
import re

class DiziYou(PluginBase):
    name     = "DiziYou"
    main_url = "https://www.diziyou1.com"

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.oturum.get(f"{self.main_url}/?s={query}")
        secici = Selector(istek.text)

        return [
            SearchResult(
                title  = afis.css("div#categorytitle a::text").get().strip(),
                url    = self.fix_url(afis.css("div#categorytitle a::attr(href)").get()),
                poster = self.fix_url(afis.css("img::attr(src)").get()),
            )
                for afis in secici.css("div.incontent div#list-series")
        ]

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.oturum.get(url)
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

    async def load_links(self, url: str) -> list[str]:
        istek  = await self.oturum.get(url)
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
                "subtitles" : subtitles
            }

        return [stream.get("url") for stream in stream_urls]

    async def play(self, name: str, url: str, referer: str, subtitles: list[Subtitle]):
        extract_result = ExtractResult(name=name, url=url, referer=referer, subtitles=subtitles)
        self.media_handler.title = name
        if self.name not in self.media_handler.title:
            self.media_handler.title = f"{self.name} | {self.media_handler.title}"

        self.media_handler.play_media(extract_result)