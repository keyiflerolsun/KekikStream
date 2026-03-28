# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re


class YoTurkish(PluginBase):
    name        = "YoTurkish"
    language    = "en"
    main_url    = "https://yoturkish.to"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "YoTurkish - is the most favorite website for watching turkish series with english subtitles for free online, only at yoturkish.to"

    main_page = {
        f"{main_url}/series/"          : "Latest Series",
        f"{main_url}/genre/adventure/" : "Adventure",
        f"{main_url}/genre/action/"    : "Action",
        f"{main_url}/genre/romance/"   : "Romance",
        f"{main_url}/genre/drama/"     : "Drama",
        f"{main_url}/genre/comedy/"    : "Comedy",
        f"{main_url}/genre/crime/"     : "Crime",
        f"{main_url}/genre/family/"    : "Family",
        f"{main_url}/genre/history/"   : "History",
        f"{main_url}/genre/mystery/"   : "Mystery",
        f"{main_url}/genre/thriller/"  : "Thriller",
        f"{main_url}/genre/war/"       : "War",
        f"{main_url}/genre/horror/"    : "Horror",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        full_url = url if page <= 1 else f"{url.rstrip('/')}/page/{page}/"
        istek    = await self.httpx.get(full_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.item.tooltipstered"):
            link   = item.select_first("a")
            title  = link.attrs.get("title") if link else None
            href   = link.attrs.get("href") if link else None
            poster = item.select_poster("img")

            if title and href:
                results.append(MainPageResult(category=category, title=title.strip(), url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        full_url = f"{self.main_url}/?s={query}"
        istek    = await self.httpx.get(full_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.item.tooltipstered"):
            link   = item.select_first("a")
            title  = link.attrs.get("title") if link else None
            href   = link.attrs.get("href") if link else None
            poster = item.select_poster("img")

            if title and href:
                results.append(SearchResult(title=title.strip(), url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("h1")
        poster      = secici.select_attr("meta[property='og:image']", "content")
        description = secici.select_text("div.desc.shorting p")

        # Meta verileri
        year = secici.extract_year("span a[href*='year/']")
        tags = secici.select_texts("span a[href*='genre/']")

        # Actors için description içindeki 'Starring:' metnine bakalım
        actors = []
        if description and "Starring:" in description:
            try:
                actors_raw = description.split("Starring:")[-1].split(".")[0].strip()
                actors     = [a.strip() for a in actors_raw.split(",") if a.strip()]
            except:
                pass

        episodes = []
        for bolum in secici.select("div#episodes a.episod"):
            name = bolum.text(strip=True)
            href = bolum.attrs.get("href")
            if href:
                _, ep_num = secici.extract_season_episode(name)
                episodes.append(
                    Episode(
                        season  = 1,
                        episode = ep_num or (len(episodes) + 1),
                        title   = f"{title} - {name}",
                        url     = self.fix_url(href),
                    )
                )

        episodes.reverse()

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title.strip() if title else "Bilinmeyen",
            description = description,
            tags        = tags,
            year        = str(year) if year else None,
            actors      = actors,
            episodes    = episodes,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        text   = istek.text
        secici = HTMLHelper(text)

        response = []
        tasks    = []

        # Sayfa içindeki tüm iframe src'lerini yakala (HTML ve Script içinden)
        sources = set(re.findall(r'src=["\'](https?://[^"\']+)["\']', text))

        for src in sources:
            src = self.fix_url(src)
            # Reklam, JS, CDN veya geçersiz yapıları atla
            if any(x in src.lower() for x in [
                "google", "facebook", "ads", "analytics", "data:image",
                "gb.ligninkeftiu.com", "cloudflare", "sharethis",
                "wp-content/", "wp-includes/", "pubadx", "bvtpk.com",
            ]):
                continue
            if src.lower().endswith((".js", ".css", ".png", ".jpg", ".gif", ".svg", ".ico")):
                continue

            tasks.append(self.extract(src, referer=url))

        results = await self.gather_with_limit(tasks)
        for res in results:
            self.collect_results(response, res)

        return response
