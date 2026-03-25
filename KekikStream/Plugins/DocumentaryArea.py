# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper
import re


class DocumentaryArea(PluginBase):
    name        = "DocumentaryArea"
    language    = "en"
    main_url    = "https://www.documentaryarea.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Watch the best online documentary films.Stunning collection of awesome, eyeopening, interesting, just released, full documentaries."

    main_page = {
        f"{main_url}/"                       : "Newly Added",
        f"{main_url}/category/History/"      : "History",
        f"{main_url}/category/War/"          : "War",
        f"{main_url}/category/Science/"      : "Science",
        f"{main_url}/category/Astronomy/"    : "Astronomy",
        f"{main_url}/category/Space/"        : "Space",
        f"{main_url}/category/Technology/"   : "Technology",
        f"{main_url}/category/Nature/"       : "Nature",
        f"{main_url}/category/Wildlife/"     : "Wildlife",
        f"{main_url}/category/Biographies/"  : "Biographies",
        f"{main_url}/category/Art/"          : "Art",
        f"{main_url}/category/Architecture/" : "Architecture",
        f"{main_url}/category/Environment/"  : "Environment",
        f"{main_url}/category/Health/"       : "Health",
        f"{main_url}/category/Mystery/"      : "Mystery",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        is_home = url.rstrip("/") == self.main_url
        if page == 1:
            full_url = url
        else:
            if is_home:
                full_url = f"{self.main_url}/?pageNum_Recordset1={page - 1}"
            else:
                full_url = f"{url.rstrip('/')}/page/{page}/"

        istek  = await self.httpx.get(full_url)
        secici = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.col-md-8 article"):
            link   = item.select_first("h2 a")
            title  = link.text(strip=True) if link else None
            href   = link.attrs.get("href") if link else None
            poster = item.select_poster("img")

            if title and href:
                results.append(MainPageResult(category=category, title=title, url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        full_url = f"{self.main_url}/results/search={query}"
        istek    = await self.httpx.get(full_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.col-md-8 article"):
            link   = item.select_first("h2 a")
            title  = link.text(strip=True) if link else None
            href   = link.attrs.get("href") if link else None
            poster = item.select_poster("img")

            if title and href:
                results.append(SearchResult(title=title, url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url, follow_redirects=True)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("h1") or secici.select_attr("meta[property='og:title']", "content")
        poster      = secici.select_attr("meta[property='og:image']", "content") or secici.select_poster("div#imagen img")
        description = secici.select_text("div.comments") or secici.select_attr("meta[name='Description']", "content")

        # Meta verileri (Isabetli yakalama)
        year = secici.select_attr("meta[itemprop='dateCreated']", "content") or secici.regex_first(r"\b(20\d{2}|19\d{2})\b")
        tags = secici.select_texts("div.s-author p a[href*='genre=']") or secici.meta_list("Keywords")

        # Fallback for tags from meta keywords
        if not tags:
            keywords = secici.select_attr("meta[name='Keywords']", "content")
            if keywords:
                tags = [t.strip() for t in keywords.split(",") if t.strip()]

        # Actors/Director meta alanı
        actors = secici.select_texts("div.s-author p a:not([href*='genre='])")
        if not actors:
            # Sayfa içinde label bazlı arama
            actors = secici.meta_list("Director") or secici.meta_list("Host") or secici.meta_list("Cast")

        return MovieInfo(
            url         = str(istek.url),
            poster      = self.fix_url(poster),
            title       = title.strip() if title else "Bilinmeyen",
            description = description,
            tags        = tags,
            year        = str(year) if year else None,
            actors      = actors,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek = await self.httpx.get(url, follow_redirects=True)
        text  = istek.text

        response = []
        # Video linklerini regex ile yakala (file: "...")
        video_matches = re.findall(r'file:\s*"(https?://[^"]+video(?:HD)?\.php[^"]*)"', text)

        # Altyazıları yakala
        subtitles   = []
        sub_matches = re.findall(r'tracks:\s*\[\s*\{\s*file:\s*"([^"]+)",\s*label:\s*"([^"]+)"', text)
        for s_url, s_label in sub_matches:
            from KekikStream.Core import Subtitle

            subtitles.append(Subtitle(name=s_label, url=self.fix_url(s_url)))

        for vid_url in video_matches:
            quality = "HD" if "videoHD.php" in vid_url else "SD"
            response.append(ExtractResult(name=f"{self.name} | {quality}", url=self.fix_url(vid_url), referer=url, subtitles=subtitles))

        return response
