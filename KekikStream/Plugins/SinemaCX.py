# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, Subtitle, ExtractResult
from KekikStream.Core.HTMLHelper import HTMLHelper

class SinemaCX(PluginBase):
    name        = "SinemaCX"
    language    = "tr"
    main_url    = "https://www.sinema.fit"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Türkiye'nin en iyi film platformu Sinema.cc! 2026'nın en yeni ve popüler yabancı yapımları, Türkçe dublaj ve altyazılı HD kalitede, reklamsız ve ücretsiz olarak seni bekliyor. Şimdi izle!"

    main_page   = {
        f"{main_url}/page/SAYFA"                           : "Son Eklenen Filmler",
        f"{main_url}/izle/aile-filmleri/page/SAYFA"        : "Aile Filmleri",
        f"{main_url}/izle/aksiyon-filmleri/page/SAYFA"     : "Aksiyon Filmleri",
        f"{main_url}/izle/animasyon-filmleri/page/SAYFA"   : "Animasyon Filmleri",
        f"{main_url}/izle/belgesel/page/SAYFA"             : "Belgesel Filmleri",
        f"{main_url}/izle/bilim-kurgu-filmleri/page/SAYFA" : "Bilim Kurgu Filmler",
        f"{main_url}/izle/biyografi/page/SAYFA"            : "Biyografi Filmleri",
        f"{main_url}/izle/dram-filmleri/page/SAYFA"        : "Dram Filmleri",
        f"{main_url}/izle/erotik-filmler/page/SAYFA"       : "Erotik Film",
        f"{main_url}/izle/fantastik-filmler/page/SAYFA"    : "Fantastik Filmler",
        f"{main_url}/izle/gerilim-filmleri/page/SAYFA"     : "Gerilim Filmleri",
        f"{main_url}/izle/gizem-filmleri/page/SAYFA"       : "Gizem Filmleri",
        f"{main_url}/izle/komedi-filmleri/page/SAYFA"      : "Komedi Filmleri",
        f"{main_url}/izle/korku-filmleri/page/SAYFA"       : "Korku Filmleri",
        f"{main_url}/izle/macera-filmleri/page/SAYFA"      : "Macera Filmleri",
        f"{main_url}/izle/muzikal-filmler/page/SAYFA"      : "Müzikal Filmler",
        f"{main_url}/izle/romantik-filmler/page/SAYFA"     : "Romantik Filmler",
        f"{main_url}/izle/savas-filmleri/page/SAYFA"       : "Savaş Filmleri",
        f"{main_url}/izle/seri-filmler/page/SAYFA"         : "Seri Filmler",
        f"{main_url}/izle/spor-filmleri/page/SAYFA"        : "Spor Filmleri",
        f"{main_url}/izle/suc-filmleri/page/SAYFA"         : "Suç Filmleri",
        f"{main_url}/izle/tarihi-filmler/page/SAYFA"       : "Tarih Filmler",
        f"{main_url}/izle/western-filmleri/page/SAYFA"     : "Western Filmler",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(url.replace("SAYFA", str(page)))
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.son div.frag-k, div.icerik div.frag-k"):
            title = secici.select_text("div.yanac span", veri)
            if not title:
                continue

            href = secici.select_attr("div.yanac a", "href", veri)
            poster = secici.select_attr("a.resim img", "data-src", veri) or secici.select_attr("a.resim img", "src", veri)

            results.append(MainPageResult(
                category = category,
                title    = title,
                url      = self.fix_url(href) if href else "",
                poster   = self.fix_url(poster) if poster else None,
            ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.icerik div.frag-k"):
            title = secici.select_text("div.yanac span", veri)
            if not title:
                continue

            href = secici.select_attr("div.yanac a", "href", veri)
            poster = secici.select_attr("a.resim img", "data-src", veri) or secici.select_attr("a.resim img", "src", veri)

            results.append(SearchResult(
                title  = title,
                url    = self.fix_url(href) if href else "",
                poster = self.fix_url(poster) if poster else None,
            ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("div.f-bilgi h1")
        poster      = secici.select_poster("div.resim img")
        description = secici.select_text("div.ackl div.scroll-liste")
        rating      = secici.select_text("b.puandegistir")
        tags        = secici.select_texts("div.f-bilgi div.tur a")
        year        = secici.extract_year("ul.detay a[href*='yapim']")
        actors      = secici.select_texts("li.oync li.oyuncu-k span.isim")

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster) if poster else None,
            title       = title or "Bilinmiyor",
            description = description,
            rating      = rating,
            tags        = tags,
            year        = str(year) if year else None,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        iframe_list = secici.select_attrs("iframe", "data-vsrc")

        # Sadece fragman varsa /2/ sayfasından dene
        has_only_trailer = all(
            "youtube" in (i or "").lower() or "fragman" in (i or "").lower() or "trailer" in (i or "").lower()
            for i in iframe_list
        )

        if has_only_trailer:
            alt_url   = url.rstrip("/") + "/2/"
            alt_istek = await self.httpx.get(alt_url)

            alt_sec   = HTMLHelper(alt_istek.text)
            iframe_list = alt_sec.select_attrs("iframe", "data-vsrc")

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
        sub_section = HTMLHelper(iframe_text).regex_first(r'playerjsSubtitle\s*=\s*"(.+?)"')
        if sub_section:
            for lang, link in HTMLHelper(sub_section).regex_all(r'\[(.*?)](https?://[^\s\",]+)'):
                subtitles.append(Subtitle(name=lang, url=self.fix_url(link)))

        # player.filmizle.in kontrolü
        if "player.filmizle.in" in iframe.lower():
            base_url = HTMLHelper(iframe).regex_first(r"https?://([^/]+)")
            if base_url:
                vid_id   = iframe.split("/")[-1]

                self.httpx.headers.update({"X-Requested-With": "XMLHttpRequest"})
                vid_istek = await self.httpx.post(
                    f"https://{base_url}/player/index.php?data={vid_id}&do=getVideo",
                )
                vid_data = vid_istek.json()

                if vid_data.get("securedLink"):
                    results.append(ExtractResult(
                        name      = f"{self.name}",
                        url       = vid_data["securedLink"],
                        referer   = iframe,
                        subtitles = subtitles
                    ))
        else:
            # Extractor'a yönlendir
            data = await self.extract(iframe)
            if data:
                results.append(data)

        return results
