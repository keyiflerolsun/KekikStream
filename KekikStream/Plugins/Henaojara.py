# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re


class Henaojara(PluginBase):
    name        = "Henaojara"
    language    = "mx"
    main_url    = "https://ww1.henaojara.net"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Ver anime online, subtitulado y/o doblado al español latino HD y completamente gratis. Aquí podrás ver y descargar todas tus series preferidas sin anuncios."

    main_page = {
        main_url                                           : "Episodios Nuevos",
        f"{main_url}/animes?tipo=anime"             : "Animes",
        f"{main_url}/animes?tipo=pelicula"          : "Películas",
        f"{main_url}/animes?genero=accion"          : "Acción",
        f"{main_url}/animes?genero=artes-marciales" : "Artes Marciales",
        f"{main_url}/animes?genero=aventura"        : "Aventura",
        f"{main_url}/animes?genero=ciencia-ficcion" : "Ciencia Ficción",
        f"{main_url}/animes?genero=comedia"         : "Comedia",
        f"{main_url}/animes?genero=cyberpunk"       : "Cyberpunk",
        f"{main_url}/animes?genero=demonios"        : "Demonios",
        f"{main_url}/animes?genero=deportes"        : "Deportes",
        f"{main_url}/animes?genero=drama"           : "Drama",
        f"{main_url}/animes?genero=ecchi"           : "Ecchi",
        f"{main_url}/animes?genero=escuela"         : "Escuela",
        f"{main_url}/animes?genero=fantasia"        : "Fantasía",
        f"{main_url}/animes?genero=gore"            : "Gore",
        f"{main_url}/animes?genero=harem"           : "Harem",
        f"{main_url}/animes?genero=horror"          : "Horror",
        f"{main_url}/animes?genero=isekai"          : "Isekai",
        f"{main_url}/animes?genero=magia"           : "Magia",
        f"{main_url}/animes?genero=mecha"           : "Mecha",
        f"{main_url}/animes?genero=misterio"        : "Misterio",
        f"{main_url}/animes?genero=psicologico"     : "Psicológico",
        f"{main_url}/animes?genero=romance"         : "Romance",
        f"{main_url}/animes?genero=seinen"          : "Seinen",
        f"{main_url}/animes?genero=shounen"         : "Shounen",
        f"{main_url}/animes?genero=sobrenatural"    : "Sobrenatural",
        f"{main_url}/animes?genero=suspenso"        : "Suspenso",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        is_home = category == "Episodios Nuevos"
        if page <= 1:
            full_url = url
        else:
            sep      = "&" if "?" in url else "?"
            full_url = f"{url}{sep}pag={page}"

        istek  = await self.httpx.get(full_url)
        secici = HTMLHelper(istek.text)

        selector = "div.ul.hm article.li" if is_home else "div.ul article.li"
        results  = []
        for item in secici.select(selector):
            link  = item.select_first("h3.h a") or item.select_first("a")
            title = link.text(strip=True) if link else None
            href  = link.attrs.get("href") if link else None

            if not href or any(x in href.lower() for x in ["noticias", "somoskudasai", "kudasai"]):
                continue

            ep = item.select_text("b.e")
            if ep:
                title = f"{title} - {ep}"

            poster = item.select_poster("img")

            if title and href:
                results.append(MainPageResult(category=category, title=title.strip(), url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        full_url = f"{self.main_url}/animes?buscar={query}"
        istek    = await self.httpx.get(full_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.ul article.li"):
            link   = item.select_first("h3.h a") or item.select_first("a")
            title  = link.text(strip=True) if link else None
            href   = link.attrs.get("href") if link else None
            poster = item.select_poster("img")

            if title and href:
                results.append(SearchResult(title=title.strip(), url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        if "/ver/" in url:
            main_link = secici.select_attr("li.ls a", "href")
            if main_link:
                return await self.load_item(self.fix_url(main_link))

        title       = secici.select_text("div.info-b h1")
        poster      = secici.select_poster("div.info-a img")
        description = secici.select_text("div.tx p")
        tags        = secici.select_texts("ul.gn li a")

        # Meta verileri (İspanyolca etiketler)
        year = secici.meta_value("Año") or secici.meta_value("Estreno") or secici.meta_value("Emisión")
        if not year:
            year = secici.regex_first(r"\b(20\d{2}|19\d{2})\b", target=title)

        actors = secici.meta_list("Reparto") or secici.meta_list("Voces") or secici.meta_list("Cast")

        episodes    = []
        script_data = secici.regex_first(r"var eps = (\[.*?\]);")
        if script_data:
            matches = re.findall(r'\["(\d+)","(\d+)","(.*?)"\]', script_data)
            slug    = secici.select_attr("div.th", "data-sl") or url.rstrip("/").split("/")[-1]

            for num, _, code in matches:
                ep_url = f"{self.main_url}/ver/{slug}-{num}-{code}" if code else f"{self.main_url}/ver/{slug}-{num}"
                episodes.append(Episode(season=1, episode=int(num), title=f"Episodio {num}", url=ep_url))

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
        secici = HTMLHelper(istek.text)

        encrypt_data = secici.select_attr(".opt", "data-encrypt")
        if not encrypt_data:
            # Direkt iframe'leri tara
            response = []
            for iframe in secici.select("iframe[src]"):
                src = self.fix_url(iframe.attrs.get("src"))
                if not any(x in src.lower() for x in ["google", "facebook", "ads", "analytics"]):
                    data = await self.extract(src, referer=url)
                    self.collect_results(response, data)
            return response

        resp = await self.httpx.post(
            f"{self.main_url}/hj",
            data    = {"acc": "opt", "i": encrypt_data},
            headers = {"Referer": url, "X-Requested-With": "XMLHttpRequest"},
        )

        response = []
        # Hex links içindeki video hostlarını yakala
        hex_links = re.findall(r'encrypt=["\']([0-9a-fA-F]+)["\']', resp.text)

        for h_str in hex_links:
            try:
                decoded_url = bytes.fromhex(h_str).decode("utf-8")
                if decoded_url.startswith("http"):
                    target = self.fix_url(decoded_url)
                    if not any(x in target.lower() for x in ["google", "facebook", "ads", "bio", "data:image"]):
                        data = await self.extract(target, referer=url)
                        self.collect_results(response, data)
            except:
                pass

        return response
