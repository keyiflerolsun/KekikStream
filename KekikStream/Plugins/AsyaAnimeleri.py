# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
import base64
import re


class AsyaAnimeleri(PluginBase):
    name        = "AsyaAnimeleri"
    language    = "tr"
    main_url    = "https://asyaanimeleri.top"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Anime izle | Donghua izle | Animeler | Türkanime | Donghua Anime, Türkçe Altyazılı Anime izle , Türkçe Anime, animeizle"

    main_page = {
        f"{main_url}/series/"      : "Son Eklenenler",
        f"{main_url}/tur/anime/"   : "Animeler",
        f"{main_url}/tur/donghua/" : "Donghualar",
        f"{main_url}/tur/isekai/"  : "Isekai",
        f"{main_url}/tur/mecha/"   : "Mecha",
        f"{main_url}/tur/oyun/"    : "Oyun",
        f"{main_url}/tur/vampir/"  : "Vampir",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        if page == 1:
            full_url = url
        else:
            if "/page/" in url:
                full_url = re.sub(r"/page/\d+/?", f"/page/{page}/", url)
            else:
                full_url = f"{url.rstrip('/')}/page/{page}/"

        return await self.search_helper(full_url, category)

    async def search(self, query: str) -> list[SearchResult]:
        target_url = f"{self.main_url}/?s={query}"
        results    = []

        try:
            istek = await self.httpx.get(target_url)
            veri  = HTMLHelper(istek.text)

            for item in veri.select("article.bs"):
                title      = item.select_text("h2[itemprop='headline']")
                url_raw    = item.select_attr("a[itemprop='url']", "href")
                poster_raw = item.select_poster("img.ts-post-image")

                if title and url_raw:
                    results.append(SearchResult(title=title, url=self.fix_url(url_raw), poster=self.fix_url(poster_raw) if poster_raw else ""))
        except Exception as e:
            print(f"AsyaAnimeleri Search Error: {e}")

        return results

    async def search_helper(self, url: str, category: str) -> list[MainPageResult]:
        """Helper to parse main page results similar to search but returning MainPageResult"""
        results = []
        try:
            istek = await self.httpx.get(url)
            veri  = HTMLHelper(istek.text)

            for item in veri.select("article.bs"):
                title      = item.select_text("h2[itemprop='headline']")
                url_raw    = item.select_attr("a[itemprop='url']", "href")
                poster_raw = item.select_poster("img.ts-post-image")

                if title and url_raw:
                    results.append(MainPageResult(category=category, title=title, url=self.fix_url(url_raw), poster=self.fix_url(poster_raw) if poster_raw else ""))
        except Exception as e:
            print(f"AsyaAnimeleri Helper Error: {e}")

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek = await self.httpx.get(url)
        veri  = HTMLHelper(istek.text)

        title       = veri.select_text("h1.entry-title") or veri.select_text("h1")
        description = veri.select_text("div.entry-content") or veri.select_text("div.desc")
        poster      = veri.select_poster("img.ts-post-image") or veri.select_poster("div.thumb img")

        # Tags/Genres
        tags = veri.select_texts("div.genxed a") or veri.select_texts("span.genres a")

        # Meta
        year   = veri.meta_value("Yayın Yılı") or veri.meta_value("Yıl") or veri.extract_year(".split", ".spe span")
        actors = veri.meta_list("Oyuncular") or veri.meta_list("Kadro")

        episodes = []

        for item in veri.select("div.eplister ul li"):
            try:
                ep_url_raw = item.select_attr("a", "href")
                if not ep_url_raw:
                    continue

                ep_url   = self.fix_url(ep_url_raw)
                ep_num   = item.select_text("div.epl-num")
                ep_title = item.select_text("div.epl-title")

                full_title = f"{ep_num} - {ep_title}" if ep_num else ep_title

                s_num, e_num = 1, 0
                if ep_num:
                    try:
                        e_num = int(ep_num)
                    except:
                        pass

                episodes.append(Episode(season=s_num, episode=e_num, title=full_title, url=ep_url))
            except Exception as e:
                print(f"Error parsing episode: {e}")
                continue

        return SeriesInfo(url=url, title=title, poster=self.fix_url(poster) if poster else "", description=description, tags=tags, year=str(year) if year else None, actors=actors, episodes=episodes)

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek = await self.httpx.get(url)
        veri  = HTMLHelper(istek.text)

        links = []

        options = veri.select("select.mirror option")

        for opt in options:
            val  = opt.attrs.get("value")
            name = opt.text(strip=True)

            if not val:
                continue

            try:
                decoded_bytes = base64.b64decode(val)
                decoded_str   = decoded_bytes.decode("utf-8")

                match = re.search(r'src=["\']([^"\']+)["\']', decoded_str)
                if match:
                    src = match.group(1)
                    if src.startswith("//"):
                        src = "https:" + src
                    if "gdplayer.to/" in src and "/embed/" in src:
                        src = src.replace("gdplayer.to/embed/", "vidmoly.to/embed-") + ".html"

                    data = await self.extract(src, referer=self.main_url)
                    self.collect_results(links, data)

            except Exception as e:
                print(f"Error decoding link {name}: {e}")
                continue

        return self.deduplicate(links)
