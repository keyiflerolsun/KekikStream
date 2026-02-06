# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, Subtitle, ExtractResult, HTMLHelper
import asyncio, contextlib

class SinemaCX(PluginBase):
    name        = "SinemaCX"
    language    = "tr"
    main_url    = "https://www.sinema.news"
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

            href   = secici.select_attr("div.yanac a", "href", veri)
            poster = secici.select_attr("a.resim img", "data-src", veri) or secici.select_attr("a.resim img", "src", veri)

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
        for veri in secici.select("div.icerik div.frag-k"):
            title = secici.select_text("div.yanac span", veri)
            if not title:
                continue

            href   = secici.select_attr("div.yanac a", "href", veri)
            poster = secici.select_attr("a.resim img", "data-src", veri) or secici.select_attr("a.resim img", "src", veri)

            results.append(SearchResult(
                title  = title,
                url    = self.fix_url(href),
                poster = self.fix_url(poster),
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
        _duration   = secici.regex_first(r"<span>Süre:\s*</span>\s*(\d+)")
        duration    = int(_duration) if _duration else None

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            rating      = rating,
            tags        = tags,
            year        = year,
            actors      = actors,
            duration    = duration,
        )

    async def _get_iframe_from_source(self, text: str) -> str | None:
        """Verilen sayfa kaynağındaki iframe'i (data-vsrc veya src) bulur."""
        secici = HTMLHelper(text)

        # Öncelik data-vsrc
        if src := secici.select_attr("iframe", "data-vsrc"):
            return self.fix_url(src.split("?img=")[0])

        # Sonra src
        if src := secici.select_attr("iframe", "src"):
            return self.fix_url(src)

        return None

    async def _process_player(self, iframe_url: str, name: str) -> list[ExtractResult]:
        """Iframe URL'ini işler ve sonuç döndürür."""
        results = []

        if "player.filmizle.in" in iframe_url.lower():
            with contextlib.suppress(Exception):
                # Referer önemli
                self.httpx.headers.update({"Referer": f"{self.main_url}/"})

                # Iframe içeriğini çek (Altyazı ve JS için)
                iframe_resp = await self.httpx.get(iframe_url)
                iframe_text = iframe_resp.text

                subtitles = []
                if sub_section := HTMLHelper(iframe_text).regex_first(r'playerjsSubtitle\s*=\s*"(.+?)"'):
                    for lang, link in HTMLHelper(sub_section).regex_all(r'\[(.*?)](https?://[^\s\",]+)'):
                        subtitles.append(Subtitle(name=lang, url=self.fix_url(link)))

                base_url = HTMLHelper(iframe_url).regex_first(r"https?://([^/]+)")
                if base_url:
                    vid_id = iframe_url.split("/")[-1]
                    self.httpx.headers.update({"X-Requested-With": "XMLHttpRequest"})

                    vid_istek = await self.httpx.post(f"https://{base_url}/player/index.php?data={vid_id}&do=getVideo")
                    vid_data  = vid_istek.json()

                    if link := vid_data.get("securedLink"):
                        results.append(ExtractResult(
                            name      = name,
                            url       = link,
                            referer   = iframe_url,
                            subtitles = subtitles
                        ))
        else:
            # Standart Extractor
            with contextlib.suppress(Exception):
                extracted = await self.extract(iframe_url)
                if extracted:
                    items = extracted if isinstance(extracted, list) else [extracted]
                    for item in items:
                        item.name = name
                        results.append(item)

        return results

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek     = await self.httpx.get(url)
        main_text = istek.text
        secici    = HTMLHelper(main_text)

        sources = [] #List of tuple (url, name, needs_fetch)

        if part_list := secici.select("ul#part li, ul#f_part li"):
            for li in part_list:
                # Aktif Tab (li.tab-aktif veya span.secili)
                if "tab-aktif" in li.attrs.get("class", ""):
                     if a_tag := secici.select_first("a", li):
                         # Direkt text al (deep=False)
                         val  = a_tag.text(strip=True, deep=False)
                         name = val if val else "SinemaCX"
                         sources.append((None, name, False))

                elif span := secici.select_first("span.secili", li):
                    name = span.text(strip=True)
                    sources.append((None, name, False)) 
                
                # Pasif Tab
                elif a_tag := secici.select_first("a", li):
                    href = a_tag.attrs.get("href")
                    # title varsa title, yoksa text (deep=False ile almayı dene önce)
                    name = a_tag.attrs.get("title")
                    if not name:
                         name = a_tag.text(strip=True, deep=False)
                    if not name:
                         name = a_tag.text(strip=True) # Fallback

                    if href:
                        sources.append((self.fix_url(href), name, True))
        else:
            # Tab yoksa, tek parça filmdir.
            sources.append((None, "SinemaCX", False))

        # 2. Kaynakları İşle
        extract_tasks = []
        
        async def process_task(source):
            src_url, src_name, needs_fetch = source

            iframe_url = None
            if not needs_fetch:
                # Mevcut sayfa (main_text)
                iframe_url = await self._get_iframe_from_source(main_text)
            else:
                # Yeni sayfa fetch et
                with contextlib.suppress(Exception):
                    resp = await self.httpx.get(src_url)
                    iframe_url = await self._get_iframe_from_source(resp.text)
            
            if iframe_url:
                if "youtube.com" in iframe_url or "youtu.be" in iframe_url:
                    return []
                return await self._process_player(iframe_url, src_name)
            return []

        for src in sources:
            extract_tasks.append(process_task(src))

        results_groups = await asyncio.gather(*extract_tasks)

        final_results = []
        for group in results_groups:
            if group: 
                final_results.extend(group)

        # Duplicate Eliminasyonu
        unique_results = []
        seen = set()
        for res in final_results:
            key = (res.url, res.name)
            if res.url and key not in seen:
                unique_results.append(res)
                seen.add(key)

        return unique_results
