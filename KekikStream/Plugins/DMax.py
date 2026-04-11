# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re, contextlib

class DMax(PluginBase):
    name        = "DMax"
    language    = "tr"
    main_url    = "https://www.dmax.com.tr"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "DMAX canlı yayını, dizi ve programları yüksek kalite ve kesintisiz olarak izlemek için hemen tıkla! En sevdiğin DMAX içerikleri burada."

    _headers = {
        "User-Agent"       : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:138.0) Gecko/20100101 Firefox/138.0",
        "Accept"           : "*/*",
        "Accept-Language"  : "en-US,en;q=0.5",
        "Content-Type"     : "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With" : "XMLHttpRequest",
        "Origin"           : "https://www.dmax.com.tr",
        "Referer"          : "https://www.dmax.com.tr/",
    }

    main_page = {
        f"{main_url}/kesfet"                 : "Öne Çıkanlar",
        f"{main_url}/kesfet/a-z"             : "A-Z",
        f"{main_url}/kesfet/turbo"           : "Turbo",
        f"{main_url}/kesfet/dogayla-ic-ice"  : "Doğayla İç İçe",
        f"{main_url}/kesfet/zorlu-isler"     : "Zorlu İşler",
        f"{main_url}/kesfet/spor"            : "Spor",
        f"{main_url}/kesfet/belgesel"        : "Belgesel",
        f"{main_url}/kesfet/nasil-yapiliyor" : "Nasıl Yapılıyor?",
        f"{main_url}/kesfet/popcorn-kusagi"  : "Popcorn Kuşağı",
        f"{main_url}/kesfet/gizem-gerilim"   : "Gizem & Gerilim",
        f"{main_url}/kesfet/teknoloji"       : "Teknoloji",
        f"{main_url}/kesfet/yasam"           : "Yaşam",
    }

    def _extract_title(self, item: HTMLHelper) -> str | None:
        href  = item.select_attr("a", "href")
        title = item.select_attr("img", "alt")
        if not title:
            onclick = item.select_attr("a", "onclick")
            if onclick:
                match = re.search(r"CLICKED', '(.*?)'", onclick)
                if match:
                    title = match.group(1)
        if not title and href:
            title = href.rstrip("/").split("/")[-1].replace("-", " ").title()
        return title.strip() if title else None

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        if page > 1:
            ajax_url = f"{self.main_url}/ajax/more"
            payload  = {"type": "discover", "slug": url.split("/")[-1], "page": str(page)}
            istek    = await self.httpx.post(ajax_url, data=payload, headers=self._headers)
            html     = istek.text
        else:
            istek = await self.httpx.get(url)
            html  = istek.text

        secici  = HTMLHelper(html)
        results = []
        for item in secici.select("div.poster"):
            title  = self._extract_title(HTMLHelper(item.html))
            href   = item.select_attr("a", "href")
            poster = item.select_attr("img", "data-src") or item.select_attr("img", "src")
            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))
        return results

    async def search(self, query: str) -> list[SearchResult]:
        ajax_url = f"{self.main_url}/ajax/search"
        payload  = {"query": query}
        istek    = await self.httpx.post(ajax_url, data=payload, headers=self._headers)
        secici   = HTMLHelper(istek.text)
        results  = []
        for item in secici.select("div.poster"):
            onclick = item.select_attr("a", "onclick") or ""
            if "SEARCH_VIDEOS" in onclick:
                continue
            title  = self._extract_title(HTMLHelper(item.html))
            href   = item.select_attr("a", "href")
            poster = item.select_attr("img", "src")
            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))
        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek       = await self.httpx.get(url)
        secici      = HTMLHelper(istek.text)
        title       = secici.select_text("div.slide-title h1") or "Bilinmeyen"
        poster      = secici.select_attr("div.slide-background", "data-mobile-src")
        description = secici.select_text("div.slide-description p") or f"{title} programını DMAX farkıyla izleyin."
        program_id  = secici.select_attr("li.current a", "data-program-id")

        episodes = []
        options  = secici.select("select#video-filter-changer option")
        if options:
            for opt in options:
                szn = opt.attrs.get("value")
                if not szn:
                    continue
                ajax_url  = f"{self.main_url}/ajax/more"
                payload   = {"type": "episodes", "program_id": str(program_id), "page": "0", "season": str(szn)}
                ep_istek  = await self.httpx.post(ajax_url, data=payload, headers=self._headers)
                ep_secici = HTMLHelper(ep_istek.text)
                for ep_item in ep_secici.select("div.item a"):
                    hre = ep_item.attrs.get("href")
                    if not hre:
                        continue
                    m = re.search(r"/(\d+)-sezon-(\d+)-bolum", hre)
                    if m:
                        s, e = int(m.group(1)), int(m.group(2))
                    else:
                        s, e = HTMLHelper.extract_season_episode(hre)
                    episodes.append(Episode(
                        season  = s or int(szn),
                        episode = e or 1,
                        title   = f"{s or szn}. Sezon {e or 1}. Bölüm",
                        url     = self.fix_url(hre),
                    ))
        else:
            video_code = secici.select_attr("div.videp-player-container div", "data-video-code")
            if video_code:
                episodes.append(Episode(season=1, episode=1, title=title, url=url))

        if not episodes:
            with contextlib.suppress(Exception):
                istek_short = await self.httpx.get(f"{url}/kisa-videolar")
                sec_short   = HTMLHelper(istek_short.text)
                for item in sec_short.select("div.items a"):
                    href = item.attrs.get("href")
                    if href:
                        episodes.append(Episode(
                            title  = item.select_text("strong") or "Kısa Video",
                            url    = self.fix_url(href),
                            poster = self.fix_url(item.select_attr("img", "src")),
                        ))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            year        = "2026",
            tags        = ["Belgesel", "Macera", "Eğlence"],
            actors      = ["DMAX Sunucuları"],
            episodes    = episodes,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek      = await self.httpx.get(url)
        secici     = HTMLHelper(istek.text)
        video_code = secici.select_attr("div.videp-player-container div", "data-video-code")
        if not video_code:
            return []
        vid_url = f"https://dygvideo.dygdigital.com/api/redirect?PublisherId=27&ReferenceId={video_code}&SecretKey=NtvApiSecret2014*"
        return [ExtractResult(name=self.name, url=vid_url, referer=f"{self.main_url}/")]
