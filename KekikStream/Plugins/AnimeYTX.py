# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re
import base64
import json


class AnimeYTX(PluginBase):
    name        = "AnimeYTX"
    language    = "mx"
    main_url    = "https://animeytx.net"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Únete a la familia de AnimeYT.es y disfruta del anime online gratis. Disfruta con tus amigos del contenido más popular de la animación japonesa."

    main_page = {
        f"{main_url}/anime/"                                 : "Anime Reciente",
        f"{main_url}/tv/?type=&sub=&order="                  : "All Anime",
        f"{main_url}/tv/?status=ongoing"                     : "Ongoing",
        f"{main_url}/tv/?status=completed&type=&sub=&order=" : "Completed",
        f"{main_url}/anime-movie/"                           : "Películas",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        is_tv = "/tv/" in url
        if page <= 1:
            full_url = url
        else:
            sep      = "&" if "?" in url else "/"
            full_url = f"{url}{sep}page={page}" if is_tv else f"{url.rstrip('/')}/page/{page}/"

        istek  = await self.httpx.get(full_url)
        secici = HTMLHelper(istek.text)

        results = []
        for item in secici.select("article.bs"):
            link   = item.select_first("a")
            title  = item.select_text(".tt") or item.select_text(".tt h2")
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
        for item in secici.select("article.bs"):
            link   = item.select_first("a")
            title  = item.select_text(".tt") or item.select_text(".tt h2")
            href   = link.attrs.get("href") if link else None
            poster = item.select_poster("img")

            if title and href:
                results.append(SearchResult(title=title.strip(), url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        # Eğer tekli bölüm sayfasındaysak ana dizi sayfasına gidelim
        if "/anime/" in url:
            series_link = (
                secici.select_attr(".all-episodes a", "href") or secici.select_attr(".nvs.nv-8 a", "href") or secici.select_attr(".nvsc a", "href") or secici.select_attr("a[itemprop='item'][href*='/tv/']", "href")
            )
            if series_link:
                return await self.load_item(self.fix_url(series_link))

        title = secici.select_text("h1.entry-title") or secici.select_attr("meta[property='og:title']", "content")
        if title:
            title = title.replace("Sub Español - AnimeYT", "").strip()

        poster      = secici.select_attr(".thumb img", "data-src") or secici.select_attr("meta[property='og:image']", "content")
        description = secici.select_text(".entry-content[itemprop='description'] p") or secici.select_attr("meta[property='og:description']", "content")

        # Meta verileri (İspanyolca etiketler)
        year_raw = secici.meta_value("Estreno") or secici.meta_value("Año")
        year     = None
        if year_raw:
            m    = re.search(r"\b(19\d{2}|20\d{2})\b", str(year_raw))
            year = m.group(1) if m else None
        if not year:
            year = secici.regex_first(r"\b(20\d{2}|19\d{2})\b", target=title)

        tags   = secici.select_texts(".genxed a")
        actors = secici.select_texts(".cvactor .charname a") or secici.meta_list("Reparto") or secici.meta_list("Voces") or secici.meta_list("Actores")

        episodes = []
        for el in secici.select(".eplister ul li"):
            link = el.select_first("a")
            href = link.attrs.get("href") if link else None
            num  = el.select_text(".epl-num")
            name = el.select_text(".epl-title")

            if href:
                _, ep_num = secici.extract_season_episode(name or num or "1")
                episodes.append(Episode(season=1, episode=ep_num or (len(episodes) + 1), title=name or f"Episode {ep_num}", url=self.fix_url(href)))

        episodes.reverse()

        return SeriesInfo(url=url, poster=self.fix_url(poster), title=title.strip() if title else "Bilinmeyen", description=description, tags=tags, year=str(year) if year else None, actors=actors, episodes=episodes)

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        text   = istek.text
        secici = HTMLHelper(text)

        response = []
        tasks    = []

        async def resolve_redirect(redirect_url):
            try:
                headers   = {"Referer": url, "User-Agent": "Mozilla/5.0"}
                resp      = await self.httpx.get(redirect_url, follow_redirects=True, headers=headers, timeout=15)
                final_url = str(resp.url)

                if "mytsumi.com" in final_url:
                    return await process_mytsumi(final_url)

                if "php" not in final_url and final_url != redirect_url:
                    return await self.extract(final_url, referer=redirect_url)
            except:
                pass
            return None

        async def process_mytsumi(m_url):
            try:
                # Disclaimer sayfasını geç
                if "options.php" in m_url:
                    m_id  = re.search(r"value=([^&]+)", m_url).group(1)
                    m_url = f"https://mytsumi.com/multiplayer/contenedor.php?id={m_id}"

                r    = await self.httpx.get(m_url, headers={"Referer": url})
                tabs = re.search(r"const videoTabs = (\[.*?\]);", r.text)
                if tabs:
                    results = []
                    for tab in json.loads(tabs.group(1)):
                        t_url = tab.get("url")
                        if t_url:
                            ex = await self.extract(self.fix_url(t_url), referer=m_url)
                            if ex:
                                results.append(ex)
                    return results
            except:
                pass
            return None

        async def process_mirror(encoded_val):
            try:
                decoded    = base64.b64decode(encoded_val).decode("utf-8")
                iframe_src = re.search(r'src=["\']([^"\']+)["\']', decoded)
                if not iframe_src:
                    return None

                src = self.fix_url(iframe_src.group(1))
                if any(x in src for x in ["redirector.php", "one.php", "short.icu", "short.ink", "go.animeyt2.es", "mytsumi.com"]):
                    return await resolve_redirect(src)

                if any(x in src.lower() for x in ["google", "facebook", "ads", "bio", "data:image"]):
                    return None

                return await self.extract(src, referer=url)
            except:
                return None

        for opt in secici.select("select.mirror option"):
            val = opt.attrs.get("value")
            if val:
                tasks.append(process_mirror(val))

        # Redirection and mirror discovery
        for iframe in secici.select("iframe"):
            src = self.fix_url(iframe.attrs.get("data-src") or iframe.attrs.get("src") or "")
            if not src:
                continue

            if "mytsumi.com" in src:
                tasks.append(process_mytsumi(src))
            elif not any(x in src.lower() for x in ["google", "facebook", "ads", "analytics", "data:image"]):
                tasks.append(self.extract(src, referer=url))

        results = await self.gather_with_limit(tasks)
        for res in results:
            self.collect_results(response, res)

        return response
