# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re
import base64
import json
from urllib.parse import urlencode


class AnimeYTX(PluginBase):
    name        = "AnimeYTX"
    language    = "mx"
    main_url    = "https://wwv.animeytx.net"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Únete a la familia de AnimeYT.es y disfruta del anime online gratis. Disfruta con tus amigos del contenido más popular de la animación japonesa."

    main_page = {
        f"{main_url}/anime/"                                 : "Anime Reciente",
        f"{main_url}/tv/?type=&sub=&order="                  : "All Anime",
        f"{main_url}/tv/?status=ongoing"                     : "Ongoing",
        f"{main_url}/tv/?status=completed&type=&sub=&order=" : "Completed",
        f"{main_url}/anime-movie/"                           : "Películas",
        f"{main_url}/tv/?genre[]=accion"                     : "Acción",
        f"{main_url}/tv/?genre[]=adventure"                  : "Aventura",
        f"{main_url}/tv/?genre[]=ciencia-ficcion"            : "Ciencia ficción",
        f"{main_url}/tv/?genre[]=comedia"                    : "Comedia",
        f"{main_url}/tv/?genre[]=drama"                      : "Drama",
        f"{main_url}/tv/?genre[]=ecchi"                      : "Ecchi",
        f"{main_url}/tv/?genre[]=escolar"                    : "Escolar",
        f"{main_url}/tv/?genre[]=fantasia"                   : "Fantasía",
        f"{main_url}/tv/?genre[]=horror"                     : "Horror",
        f"{main_url}/tv/?genre[]=isekai"                     : "Isekai",
        f"{main_url}/tv/?genre[]=misterio"                   : "Misterio",
        f"{main_url}/tv/?genre[]=romance"                    : "Romance",
        f"{main_url}/tv/?genre[]=seinen"                     : "Seinen",
        f"{main_url}/tv/?genre[]=shoujo"                     : "Shoujo",
        f"{main_url}/tv/?genre[]=shounen"                    : "Shounen",
        f"{main_url}/tv/?genre[]=sobrenatural"               : "Sobrenatural",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        is_tv = "/tv/" in url
        if page <= 1:
            full_url = url
        else:
            sep      = "&" if "?" in url else "/"
            full_url = f"{url}{sep}page={page}" if is_tv else f"{url.rstrip('/')}/page/{page}/"

        istek  = await self.async_cf_get(full_url)
        secici = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.bsx"):
            title  = item.select_text("h2") or item.select_text("div.tt")
            href   = item.select_attr("a", "href")
            poster = item.select_poster("img")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title.strip(),
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        target_url = f"{self.main_url}/?s={query}"
        istek      = await self.async_cf_get(target_url)
        secici     = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.bsx"):
            title  = item.select_text("h2") or item.select_text("div.tt")
            href   = item.select_attr("a", "href")
            poster = item.select_poster("img")

            if title and href:
                results.append(SearchResult(
                    title  = title.strip(),
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("h1.entry-title") or secici.select_text("h1")
        description = secici.select_text("div.entry-content") or secici.select_text("div.desc")
        poster      = secici.select_poster("img.ts-post-image") or secici.select_poster("div.thumb img")
        tags        = secici.select_texts("div.genxed a")
        year        = secici.extract_year(".split", ".spe span")

        episodes = []
        # WPManga/AnimeXT Teması bölüm listesi
        for item in secici.select("div.eplister ul li, ul.clstyle li"):
            ep_url = item.select_attr("a", "href")
            if not ep_url:
                continue

            ep_num_text = item.select_text("div.epl-num") or item.select_text("span.leftoff")
            ep_title    = item.select_text("div.epl-title") or item.select_text("span.leftat")

            try:
                ep_num = int(re.search(r"(\d+)", ep_num_text).group(1)) if ep_num_text else 0
            except:
                ep_num = 0

            episodes.append(Episode(
                season  = 1,
                episode = ep_num,
                title   = ep_title or f"Episodio {ep_num}",
                url     = self.fix_url(ep_url),
            ))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title.strip() if title else "Bilinmeyen",
            description = description,
            tags        = tags,
            year        = str(year) if year else None,
            episodes    = episodes,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        response = []
        tasks    = []

        async def resolve_internal_player(player_url: str):
            fixed_url = self.fix_url(player_url)
            if not fixed_url or fixed_url.startswith("data:") or fixed_url.startswith("javascript:"):
                return None

            if "/new/redirector.php" in fixed_url or "/new/redirector2.php" in fixed_url:
                try:
                    redirect_resp = await self.async_cf_get(fixed_url, headers={"Referer": url})
                    redirect_html = redirect_resp.text
                    target_url    = HTMLHelper(redirect_html).regex_first(r"window\.location\.href\s*=\s*'([^']+)'")
                    if target_url:
                        target_url = target_url.replace(" ", "+")
                        return await self.extract(self.fix_url(target_url), referer=url)
                except Exception:
                    return None

            if "/new/play/one.php" not in fixed_url:
                return await self.extract(fixed_url, referer=url)

            parsed = re.search(r"server=([^&]+)&value=([^&]+)", fixed_url)
            if not parsed:
                return None

            payload = {
                "server" : parsed.group(1),
                "value"  : parsed.group(2),
            }
            try:
                ajax_resp = await self.async_cf_get(
                    f"{self.main_url}/new/play/one.php?{urlencode(payload)}",
                    headers={"Referer": url, "X-Requested-With": "XMLHttpRequest"},
                )
                body = ajax_resp.text
            except Exception:
                return None

            iframe_src = HTMLHelper(body).select_attr("iframe", "src") or HTMLHelper(body).regex_first(r'src=["\']([^"\']+)["\']')
            if not iframe_src:
                return None

            return await self.extract(self.fix_url(iframe_src), referer=url)

        # Find players in select menu (Base64 encoded iframes)
        for opt in secici.select("select.mirror option"):
            val = opt.attrs.get("value")
            if not val:
                continue

            try:
                decoded = base64.b64decode(val).decode("utf-8")
                # Extract src from <iframe src="...">
                iframe_src = re.search(r'src=["\']([^"\']+)["\']', decoded)
                if iframe_src:
                    src = iframe_src.group(1)
                    tasks.append(resolve_internal_player(src))
            except:
                continue

        # Legacy/Other patterns
        players = secici.regex_all(r"var\s+video\s*=\s*\[(.*?)\]", flags=re.S)
        if players:
            for p in players:
                urls = re.findall(r'url["\']\s*:\s*["\']([^"\']+)["\']', p)
                for u in urls:
                    tasks.append(resolve_internal_player(u.replace("\\/", "/")))

        # Check iframes
        for iframe in secici.select("iframe"):
            src = iframe.select_attr(None, "src")
            if src and not any(x in src.lower() for x in ["facebook", "google", "ads", "bio", "data:image"]):
                tasks.append(resolve_internal_player(src))

        results = await self.gather_with_limit(tasks)
        for res in results:
            self.collect_results(response, res)

        return self.deduplicate(response)
