# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
from contextlib       import suppress

class DDizi(PluginBase):
    name        = "DDizi"
    language    = "tr"
    main_url    = "https://www.ddizi.im"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Ddizi, dizi izle, dizi seyret, yerli dizi izle, canlı dizi, türk dizi izle, dizi izle full, diziizle, eski diziler"

    main_page   = {
        f"{main_url}/yeni-eklenenler7" : "Son Eklenen Bölümler",
        f"{main_url}/yabanci-dizi-izle" : "Yabancı Diziler",
        f"{main_url}/eski.diziler"       : "Eski Diziler",
        f"{main_url}/yerli-diziler"     : "Yerli Diziler"
    }

    async def get_articles(self, secici: HTMLHelper) -> list[dict]:
        articles = []
        for veri in secici.select("div.dizi-boxpost-cat, div.dizi-boxpost"):
            title = secici.select_text("a", veri)
            href  = secici.select_attr("a", "href", veri)
            img   = secici.select_first("img.img-back, img.img-back-cat", veri)
            poster = img.attrs.get("data-src") or img.attrs.get("src") if img else None

            if title and href:
                articles.append({
                    "title" : self.clean_title(title),
                    "url"   : self.fix_url(href),
                    "poster": self.fix_url(poster),
                })

        return articles

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        # DDizi'de sayfalama /sayfa-X formatında (0'dan başlıyor)
        if page > 1:
            target_url = f"{url}/sayfa-{page-1}"
        else:
            target_url = url

        istek      = await self.httpx.get(target_url, follow_redirects=True)
        secici     = HTMLHelper(istek.text)
        veriler    = await self.get_articles(secici)

        return [MainPageResult(**veri, category=category) for veri in veriler if veri]

    async def search(self, query: str) -> list[SearchResult]:
        istek = await self.httpx.post(
            url     = f"{self.main_url}/arama/",
            headers = {"Referer": f"{self.main_url}/"},
            data    = {"arama": query}
        )
        secici  = HTMLHelper(istek.text)
        veriler = await self.get_articles(secici)

        return [SearchResult(**veri) for veri in veriler if veri]

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = self.clean_title(secici.select_text("h1, h2, div.dizi-boxpost-cat a"))
        poster      = secici.select_poster("div.afis img, img.afis, img.img-back, img.img-back-cat")
        description = secici.select_text("div.dizi-aciklama, div.aciklama, p")
        rating      = secici.select_text("span.comments-ss") 
        
        # Meta verileri (DDizi'de pek yok ama deniyoruz)
        # Year için sadece açıklama kısmına bakalım ki URL'deki ID'yi almasın
        year   = HTMLHelper(description).regex_first(r"(\d{4})") if description else None
        actors = secici.select_texts("div.oyuncular a, ul.bilgi li a")
        
        episodes = []
        current_page = 1
        has_next = True
        
        while has_next:
            page_url = f"{url}/sayfa-{current_page}" if current_page > 1 else url
            if current_page > 1:
                istek = await self.httpx.get(page_url)
                secici = HTMLHelper(istek.text)
            
            page_eps = secici.select("div.bolumler a, div.sezonlar a, div.dizi-arsiv a, div.dizi-boxpost-cat a")
            if not page_eps:
                break
                
            for ep in page_eps:
                name = ep.text().strip()
                href = ep.attrs.get("href")
                if name and href:
                    # 'Bölüm Final' gibi durumları temizleyelim
                    clean_name = name.replace("Final", "").strip()
                    s, e = secici.extract_season_episode(clean_name)
                    episodes.append(Episode(
                        season  = s or 1,
                        episode = e or 1,
                        title   = name,
                        url     = self.fix_url(href)
                    ))
            
            # Sonraki sayfa kontrolü
            has_next = any("Sonraki" in a.text() for a in secici.select(".pagination a"))
            current_page += 1
            if current_page > 10:
                break # Emniyet kilidi

        if not episodes:
            s, e = secici.extract_season_episode(title)
            episodes.append(Episode(
                season  = s or 1,
                episode = e or 1,
                title   = title,
                url     = url
            ))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            rating      = rating.strip() if rating else None,
            year        = year,
            actors      = actors,
            episodes    = episodes
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        results = []
        # og:video ve JWPlayer kontrolü
        og_video = secici.select_attr("meta[property='og:video']", "content")
        if og_video:
            og_video = self.fix_url(og_video)
            with suppress(Exception):
                player_istek = await self.httpx.get(og_video, headers={"Referer": url})
                player_secici = HTMLHelper(player_istek.text)
                
                # file: '...' logic
                sources = player_secici.regex_all(r'file:\s*["\']([^"\']+)["\']')
                for src in sources:
                    src = self.fix_url(src)
                    # Direkt link kontrolü - Extractor gerektirmeyenler
                    is_direct = any(x in src.lower() for x in ["google", "twimg", "mncdn", "akamai", "streambox", ".m3u8", ".mp4", "master.txt"])
                    
                    if is_direct:
                        results.append(ExtractResult(
                            url        = src,
                            name       = "Video",
                            user_agent = "googleusercontent",
                            referer    = "https://twitter.com/"
                        ))
                    else:
                        res = await self.extract(src, referer=og_video)
                        if res:
                            if isinstance(res, list):
                                results.extend(res)
                            else:
                                results.append(res)
                
                # Fallback to direct extraction if nothing found but we have og_video
                if not results:
                    if any(x in og_video.lower() for x in ["google", "twimg", "mncdn", "akamai", "streambox", ".m3u8", ".mp4", "master.txt"]):
                        results.append(ExtractResult(
                            url        = og_video,
                            name       = "Video",
                            user_agent = "googleusercontent",
                            referer    = "https://twitter.com/"
                        ))
                    else:
                        res = await self.extract(og_video)
                        if res:
                            if isinstance(res, list):
                                results.extend(res)
                            else:
                                results.append(res)

        return results
