# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import (
    PluginBase,
    MainPageResult,
    SearchResult,
    MovieInfo,
    SeriesInfo,
    Episode,
    ExtractResult,
    HTMLHelper,
)
import re


class FlixLatam(PluginBase):
    name        = "FlixLatam"
    language    = "mx"
    main_url    = "https://flixlatam.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "FlixLatam - Películas, series y animes online en audio latino. El mejor contenido de streaming gratuito con alta calidad."

    _headers = {
        "User-Agent" : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
        "Referer"    : f"{main_url}/",
    }

    main_page = {
        f"{main_url}/peliculas"               : "Películas",
        f"{main_url}/peliculas/populares"     : "Películas Populares",
        f"{main_url}/series"                  : "Series",
        f"{main_url}/series/populares"        : "Series Populares",
        f"{main_url}/animes"                  : "Anime",
        f"{main_url}/animes/populares"        : "Anime Populares",
        f"{main_url}/generos/dorama"          : "Doramas",
        f"{main_url}/generos/accion"          : "Acción",
        f"{main_url}/generos/ciencia-ficcion" : "Ciencia Ficción",
        f"{main_url}/generos/romance"         : "Romance",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        full_url = url if page <= 1 else f"{url}?page={page}"
        istek    = await self.httpx.get(full_url, headers=self._headers)
        secici   = HTMLHelper(istek.text)

        results = []
        for item in secici.select("article.item"):
            link   = item.select_first("div.data h3 a") or item.select_first("div.poster a")
            title  = link.text(strip=True) if link else item.select_attr("div.poster img", "alt")
            href   = link.attrs.get("href") if link else None
            poster = item.select_poster("div.poster img")

            if title and href:
                results.append(MainPageResult(category=category, title=title.strip(), url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        full_url = f"{self.main_url}/search?s={query}"
        istek    = await self.httpx.get(full_url, headers=self._headers)
        secici   = HTMLHelper(istek.text)

        results = []
        for item in secici.select("article.item"):
            link   = item.select_first("div.data h3 a") or item.select_first("div.poster a")
            title  = link.text(strip=True) if link else item.select_attr("div.poster img", "alt")
            href   = link.attrs.get("href") if link else None
            poster = item.select_poster("div.poster img")

            if title and href:
                results.append(SearchResult(title=title.strip(), url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url, headers=self._headers)
        secici = HTMLHelper(istek.text)

        title = secici.select_attr("meta[property='og:title']", "content")
        if title:
            title = re.sub(r"(?i)▷? ?Ver | ?Audio Latino| ?Online| - Series Latinoamerica| - FlixLatam", "", title).strip()

        poster      = secici.select_attr("meta[property='og:image']", "content")
        description = secici.select_attr("meta[property='og:description']", "content") or secici.select_text("div.wp-content p")

        # Meta verileri (İspanyolca etiketler)
        year = secici.meta_value("Año") or secici.meta_value("Estreno") or secici.regex_first(r'datePublished"\s*:\s*"(\d{4})"')
        if not year:
            year = secici.regex_first(r"\b(20\d{2}|19\d{2})\b", target=title)

        tags   = secici.select_texts(".sgeneros a")
        rating = secici.select_text(".dt_rating_vgs")
        actors = secici.meta_list("Reparto") or secici.meta_list("Voces") or secici.meta_list("Protagonistas")

        episodes = []
        for li in secici.select("ul.episodios li"):
            ep_link   = li.select_first(".episodiotitle a")
            ep_href   = ep_link.attrs.get("href") if ep_link else None
            ep_name   = ep_link.text(strip=True) if ep_link else None
            ep_poster = li.select_poster(".imagen img")

            numerando = li.select_text(".numerando") or "1-1"
            parts     = numerando.split("-")
            season    = int(parts[0]) if len(parts) > 0 else 1
            episode   = int(parts[-1]) if len(parts) > 1 else 1

            if ep_href:
                episodes.append(
                    Episode(
                        season  = season,
                        episode = episode,
                        title   = ep_name or f"Episodio {episode}",
                        url     = self.fix_url(ep_href),
                        poster  = self.fix_url(ep_poster),
                    )
                )

        if episodes:
            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = title or "Bilinmeyen",
                description = description,
                tags        = tags,
                year        = str(year) if year else None,
                rating      = rating,
                actors      = actors,
                episodes    = episodes,
            )

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title or "Bilinmeyen",
            description = description,
            tags        = tags,
            year        = str(year) if year else None,
            actors      = actors,
            rating      = rating,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url, headers=self._headers)
        secici = HTMLHelper(istek.text)

        iframe = secici.select_attr("div.play iframe", "src") or secici.select_attr("iframe[src*='embed69']", "src")
        if not iframe:
            # Sayfadaki tüm iframe'leri tara
            iframes = secici.select_attrs("iframe", "src")
            for src in iframes:
                if any(x in src for x in ["embed69", "dintezuvio", "bysedikamoum"]):
                    iframe = src
                    break

        if not iframe:
            return []

        response = []
        await self._resolve_embed69(self.fix_url(iframe), url, response)
        return response

    async def _resolve_embed69(self, url: str, referer: str, response: list):
        """Embed69 linklerini çözen recursive fonksiyon."""
        try:
            r    = await self.httpx.get(url, headers={"Referer": referer})
            html = r.text

            tokens = list(set(re.findall(r"eyJ[a-zA-Z0-9._-]+", html)))
            tokens = [t for t in tokens if len(t) > 50]

            if tokens:
                host        = url.split("//")[-1].split("/")[0]
                decrypt_api = f"https://{host}/api/decrypt"

                r_dec = await self.httpx.post(
                    decrypt_api,
                    headers = {"Content-Type": "application/json", "Referer": url, "X-Requested-With": "XMLHttpRequest"},
                    json    = {"links": tokens},
                )

                if r_dec.status_code == 200:
                    data = r_dec.json()
                    if data.get("success"):
                        links = data.get("links", [])
                        for item in links:
                            link = item.get("link") if isinstance(item, dict) else str(item)
                            link = self.fix_url(link.replace("`", "").strip())

                            if "embed69" in link or "dintezuvio" in link:
                                await self._resolve_embed69(link, url, response)
                            else:
                                if any(x in link.lower() for x in ["google", "facebook", "ads", "bio", "data:image"]):
                                    continue

                                # Bilinen hostları düzelt
                                link = link.replace("dintezuvio.com", "vidhide.com").replace("hglink.to", "streamwish.to").replace("minochinos.com", "vidhide.com").replace("ghbrisk.com", "streamwish.to")

                                data = await self.extract(link, referer=url)
                                self.collect_results(response, data)
        except:
            pass
