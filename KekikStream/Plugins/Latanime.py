# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
import base64


class Latanime(PluginBase):
    name        = "Latanime"
    language    = "mx"
    main_url    = "https://latanime.org"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Latanime - Ver anime online gratis en español latino y subtitulado. La mejor calidad en streaming para los amantes del anime."

    main_page = {
        "animes?fecha=false&genero=false&letra=false&categoria=anime"               : "Anime",
        "animes?fecha=false&genero=false&letra=false&categoria=ova"                 : "Ova",
        "animes?fecha=false&genero=false&letra=false&categoria=Película"            : "Película",
        "animes?fecha=false&genero=false&letra=false&categoria=especial"            : "Especial",
        "animes?fecha=false&genero=false&letra=false&categoria=corto"               : "Corto",
        "animes?fecha=false&genero=false&letra=false&categoria=ona"                 : "Ona",
        "animes?fecha=false&genero=false&letra=false&categoria=donghua"             : "Donghua",
        "animes?fecha=false&genero=false&letra=false&categoria=sin-censura"         : "Sin Censura",
        "animes?fecha=false&genero=false&letra=false&categoria=pelicula-1080p"      : "Pelicula 1080p",
        "animes?fecha=false&genero=false&letra=false&categoria=latino"              : "Latino",
        "animes?fecha=false&genero=false&letra=false&categoria=Película Latino"     : "Pelicula Latino",
        "animes?fecha=false&genero=false&letra=false&categoria=castellano"          : "Castellano",
        "animes?fecha=false&genero=false&letra=false&categoria=Película Castellano" : "Pelicula Castellano",
        "animes?fecha=false&genero=false&letra=false&categoria=ova-latino"          : "Ova Latino",
        "animes?fecha=false&genero=false&letra=false&categoria=ova-castellano"      : "Ova Castellano",
        "animes?fecha=false&genero=false&letra=false&categoria=latino-sin-censura"  : "Latino Sin Censura",
        "animes?fecha=false&genero=false&letra=false&categoria=live-action"         : "Live Action",
        "animes?fecha=false&genero=false&letra=false&categoria=Cartoon"             : "Cartoon",
        "animes?fecha=false&genero=false&letra=false&categoria=catalan"             : "Catalán",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        full_url = f"{self.main_url}/{url}&p={page}"
        istek    = await self.httpx.get(full_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.row a"):
            title  = item.select_text("h3")
            href   = item.attrs.get("href")
            poster = item.select_poster("img")

            if title and href:
                results.append(MainPageResult(category=category, title=title.strip(), url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        full_url = f"{self.main_url}/buscar?q={query}"
        istek    = await self.httpx.get(full_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.row a"):
            title  = item.select_text("h3")
            href   = item.attrs.get("href")
            poster = item.select_poster("img")

            if title and href:
                results.append(SearchResult(title=title.strip(), url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("h2")
        poster      = secici.select_attr("meta[property='og:image']", "content")
        description = secici.select_text("h2 ~ p.my-2")
        tags        = secici.select_texts("a div.btn")
        year        = secici.select_text(".span-tiempo").split(" de ")[-1]

        eps_anchor = secici.select("div.row a[href*='/ver/']")

        if len(eps_anchor) > 1:
            episodes = []
            for ep in eps_anchor:
                ep_href   = ep.attrs.get("href")
                ep_poster = ep.select_attr("img", "data-src")

                # Bölüm numarasını URL'den veya metinden çıkaralım
                _, ep_num = secici.extract_season_episode(ep_href)

                if ep_href:
                    episodes.append(
                        Episode(
                            season  = 1,
                            episode = ep_num or (len(episodes) + 1),
                            title   = f"Episodio {ep_num or (len(episodes) + 1)}",
                            url     = self.fix_url(ep_href),
                            poster  = self.fix_url(ep_poster),
                        )
                    )

            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = title.strip() if title else "Bilinmeyen",
                description = description,
                tags        = tags,
                year        = str(year) if year and year.isdigit() else None,
                episodes    = episodes,
            )

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title.strip() if title else "Bilinmeyen",
            description = description,
            tags        = tags,
            year        = str(year) if year and year.isdigit() else None,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        response = []
        for item in secici.select("#play-video a"):
            encoded = item.attrs.get("data-player")
            if encoded:
                try:
                    # Base64 decode ve içinden linki ayıkla
                    decoded = base64.b64decode(encoded).decode("utf-8")
                    target  = decoded.split("=")[-1] if "=" in decoded else decoded

                    if target.startswith("http"):
                        data = await self.extract(target, referer=url)
                        self.collect_results(response, data)
                except:
                    pass

        return response
