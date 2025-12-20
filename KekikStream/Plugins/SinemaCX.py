# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, Subtitle
from parsel import Selector
import re

class SinemaCX(PluginBase):
    name        = "SinemaCX"
    language    = "tr"
    main_url    = "https://www.sinema.fit"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Türkiye'nin en iyi film platformu Sinema.cc! 2026'nın en yeni ve popüler yabancı yapımları, Türkçe dublaj ve altyazılı HD kalitede, reklamsız ve ücretsiz olarak seni bekliyor. Şimdi izle!"

    main_page   = {
        f"{main_url}/page/SAYFA"                            : "Son Eklenen Filmler",
        f"{main_url}/izle/aile-filmleri/page/SAYFA"         : "Aile Filmleri",
        f"{main_url}/izle/aksiyon-filmleri/page/SAYFA"      : "Aksiyon Filmleri",
        f"{main_url}/izle/animasyon-filmleri/page/SAYFA"    : "Animasyon Filmleri",
        f"{main_url}/izle/belgesel/page/SAYFA"              : "Belgesel Filmleri",
        f"{main_url}/izle/bilim-kurgu-filmleri/page/SAYFA"  : "Bilim Kurgu Filmler",
        f"{main_url}/izle/biyografi/page/SAYFA"             : "Biyografi Filmleri",
        f"{main_url}/izle/fantastik-filmler/page/SAYFA"     : "Fantastik Filmler",
        f"{main_url}/izle/gizem-filmleri/page/SAYFA"        : "Gizem Filmleri",
        f"{main_url}/izle/komedi-filmleri/page/SAYFA"       : "Komedi Filmleri",
        f"{main_url}/izle/korku-filmleri/page/SAYFA"        : "Korku Filmleri",
        f"{main_url}/izle/macera-filmleri/page/SAYFA"       : "Macera Filmleri",
        f"{main_url}/izle/romantik-filmler/page/SAYFA"      : "Romantik Filmler",
        f"{main_url}/izle/erotik-filmler/page/SAYFA"        : "Erotik Film",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(url.replace("SAYFA", str(page)))
        secici = Selector(istek.text)

        return [
            MainPageResult(
                category = category,
                title    = veri.css("div.yanac span::text").get(),
                url      = self.fix_url(veri.css("div.yanac a::attr(href)").get()),
                poster   = self.fix_url(veri.css("a.resim img::attr(data-src)").get() or veri.css("a.resim img::attr(src)").get()),
            )
                for veri in secici.css("div.son div.frag-k, div.icerik div.frag-k")
                    if veri.css("div.yanac span::text").get()
        ]

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = Selector(istek.text)

        return [
            SearchResult(
                title  = veri.css("div.yanac span::text").get(),
                url    = self.fix_url(veri.css("div.yanac a::attr(href)").get()),
                poster = self.fix_url(veri.css("a.resim img::attr(data-src)").get() or veri.css("a.resim img::attr(src)").get()),
            )
                for veri in secici.css("div.icerik div.frag-k")
                    if veri.css("div.yanac span::text").get()
        ]

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        duration_match = re.search(r"Süre:.*?(\d+)\s*Dakika", istek.text)
        description = secici.css("div.ackl div.scroll-liste::text").get()

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(secici.css("link[rel='image_src']::attr(href)").get()),
            title       = secici.css("div.f-bilgi h1::text").get(),
            description = description.strip() if description else None,
            tags        = [a.css("::text").get() for a in secici.css("div.f-bilgi div.tur a")],
            year        = secici.css("div.f-bilgi ul.detay a[href*='yapim']::text").get(),
            actors      = [li.css("span.isim::text").get() for li in secici.css("li.oync li.oyuncu-k")],
            duration    = int(duration_match[1]) if duration_match else None,
        )

    async def load_links(self, url: str) -> list[dict]:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        iframe_list = [iframe.css("::attr(data-vsrc)").get() for iframe in secici.css("iframe")]
        iframe_list = [i for i in iframe_list if i]

        # Sadece fragman varsa /2/ sayfasından dene
        has_only_trailer = all(
            "youtube" in (i or "").lower() or "fragman" in (i or "").lower() or "trailer" in (i or "").lower()
            for i in iframe_list
        )

        if has_only_trailer:
            alt_url   = url.rstrip("/") + "/2/"
            alt_istek = await self.httpx.get(alt_url)
            alt_sec   = Selector(alt_istek.text)
            iframe_list = [iframe.css("::attr(data-vsrc)").get() for iframe in alt_sec.css("iframe")]
            iframe_list = [i for i in iframe_list if i]

        if not iframe_list:
            return []

        iframe = self.fix_url(iframe_list[0].split("?img=")[0])
        if not iframe:
            return []

        results = []

        # Altyazı kontrolü
        self.httpx.headers.update({"Referer": f"{self.main_url}/"})
        iframe_istek = await self.httpx.get(iframe)
        iframe_text  = iframe_istek.text

        subtitles = []
        sub_match = re.search(r'playerjsSubtitle\s*=\s*"(.+?)"', iframe_text)
        if sub_match:
            sub_section = sub_match[1]
            for sub in re.finditer(r'\[(.*?)](https?://[^\s",]+)', sub_section):
                subtitles.append(Subtitle(name=sub[1], url=self.fix_url(sub[2])))

        # player.filmizle.in kontrolü
        if "player.filmizle.in" in iframe.lower():
            base_match = re.search(r"https?://([^/]+)", iframe)
            if base_match:
                base_url = base_match[1]
                vid_id   = iframe.split("/")[-1]

                self.httpx.headers.update({"X-Requested-With": "XMLHttpRequest"})
                vid_istek = await self.httpx.post(
                    f"https://{base_url}/player/index.php?data={vid_id}&do=getVideo",
                )
                vid_data = vid_istek.json()

                if vid_data.get("securedLink"):
                    results.append({
                        "name"      : f"{self.name}",
                        "url"       : vid_data["securedLink"],
                        "referer"   : iframe,
                        "subtitles" : subtitles
                    })
        else:
            # Extractor'a yönlendir
            extractor = self.ex_manager.find_extractor(iframe)
            data      = await extractor.extract(iframe, referer=f"{self.main_url}/")
            results.append(data.dict())

        return results

    async def play(self, **kwargs):
        extract_result = ExtractResult(**kwargs)
        self.media_handler.title = kwargs.get("name")
        if self.name not in self.media_handler.title:
            self.media_handler.title = f"{self.name} | {self.media_handler.title}"

        self.media_handler.play_media(extract_result)
