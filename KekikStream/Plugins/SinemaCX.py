# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, Subtitle, ExtractResult
from selectolax.parser import HTMLParser
import re

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
        secici = HTMLParser(istek.text)

        results = []
        for veri in secici.css("div.son div.frag-k, div.icerik div.frag-k"):
            span_el = veri.css_first("div.yanac span")
            if not span_el:
                continue

            title = span_el.text(strip=True)
            if not title:
                continue

            link_el = veri.css_first("div.yanac a")
            img_el  = veri.css_first("a.resim img")

            href   = link_el.attrs.get("href") if link_el else None
            poster = (img_el.attrs.get("data-src") or img_el.attrs.get("src")) if img_el else None

            results.append(MainPageResult(
                category = category,
                title    = title,
                url      = self.fix_url(href) if href else "",
                poster   = self.fix_url(poster) if poster else None,
            ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLParser(istek.text)

        results = []
        for veri in secici.css("div.icerik div.frag-k"):
            span_el = veri.css_first("div.yanac span")
            if not span_el:
                continue

            title = span_el.text(strip=True)
            if not title:
                continue

            link_el = veri.css_first("div.yanac a")
            img_el  = veri.css_first("a.resim img")

            href   = link_el.attrs.get("href") if link_el else None
            poster = (img_el.attrs.get("data-src") or img_el.attrs.get("src")) if img_el else None

            results.append(SearchResult(
                title  = title,
                url    = self.fix_url(href) if href else "",
                poster = self.fix_url(poster) if poster else None,
            ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)

        duration_match = re.search(r"Süre:.*?(\d+)\s*Dakika", istek.text)

        desc_el     = secici.css_first("div.ackl div.scroll-liste")
        description = desc_el.text(strip=True) if desc_el else None

        link_el   = secici.css_first("link[rel='image_src']")
        poster    = link_el.attrs.get("href") if link_el else None

        title_el  = secici.css_first("div.f-bilgi h1")
        title     = title_el.text(strip=True) if title_el else None

        tags      = [a.text(strip=True) for a in secici.css("div.f-bilgi div.tur a") if a.text(strip=True)]

        year_el   = secici.css_first("div.f-bilgi ul.detay a[href*='yapim']")
        year      = year_el.text(strip=True) if year_el else None

        actors    = []
        for li in secici.css("li.oync li.oyuncu-k"):
            isim_el = li.css_first("span.isim")
            if isim_el and isim_el.text(strip=True):
                actors.append(isim_el.text(strip=True))

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster) if poster else None,
            title       = title,
            description = description,
            tags        = tags,
            year        = year,
            actors      = actors,
            duration    = int(duration_match[1]) if duration_match else None,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLParser(istek.text)

        iframe_list = [iframe.attrs.get("data-vsrc") for iframe in secici.css("iframe") if iframe.attrs.get("data-vsrc")]

        # Sadece fragman varsa /2/ sayfasından dene
        has_only_trailer = all(
            "youtube" in (i or "").lower() or "fragman" in (i or "").lower() or "trailer" in (i or "").lower()
            for i in iframe_list
        )

        if has_only_trailer:
            alt_url   = url.rstrip("/") + "/2/"
            alt_istek = await self.httpx.get(alt_url)
            alt_sec   = HTMLParser(alt_istek.text)
            iframe_list = [iframe.attrs.get("data-vsrc") for iframe in alt_sec.css("iframe") if iframe.attrs.get("data-vsrc")]

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
