# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re


class AnimeAV(PluginBase):
    name        = "AnimeAV"
    language    = "mx"
    main_url    = "https://animeav1.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Disfruta de los últimos episodios y animes agregados en HD y Sub Español. Miles de series, películas y OVAs disponibles para ver online totalmente gratis."

    category_url = f"{main_url}/catalogo"

    main_page = {
        main_url: "Episodios Actualizados",
        "?order=latest_released": "Últimos Estrenos",
        "?genre=Acción": "Acción",
        "?genre=Aventura": "Aventura",
        "?genre=Fantasía": "Fantasía",
        "?genre=Comedia": "Comedia",
        "?genre=Escolares": "Escolares",
        "?genre=Sobrenatural": "Sobrenatural",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        if url == self.main_url:
            full_url = url
        else:
            full_url = f"{self.category_url}{url}"
            if page > 1:
                full_url = f"{full_url}&page={page}"

        istek  = await self.httpx.get(full_url)
        secici = HTMLHelper(istek.text)

        if url == self.main_url:
            container = secici.select("section div.grid article")
        else:
            container = secici.select("div.grid.grid-cols-2 article")

        results = []
        for item in container:
            link   = item.select_first("a")
            title  = item.select_text("h3") or item.select_text("span.sr-only")
            href   = link.attrs.get("href") if link else None
            poster = item.select_poster("img")

            if title and href:
                results.append(MainPageResult(category=category, title=title.strip(), url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        full_url = f"{self.main_url}/catalogo?search={query}"
        istek    = await self.httpx.get(full_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.grid.grid-cols-2 article"):
            link   = item.select_first("a")
            title  = item.select_text("h3") or item.select_text("span.sr-only")
            href   = link.attrs.get("href") if link else None
            poster = item.select_poster("img")

            if title and href:
                results.append(SearchResult(title=title.strip(), url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        request_url = url.rsplit("/", 1)[0] if re.search(r"/\d+$", url) else url
        istek       = await self.httpx.get(request_url, headers={"Referer": f"{self.main_url}/"})
        secici      = HTMLHelper(istek.text)

        title       = secici.select_text("h1")
        poster      = secici.select_attr("img.aspect-poster", "src")
        description = secici.select_text("div.entry.text-lead p")
        tags        = secici.select_texts("div.flex-wrap.gap-2 a[href*='genre']")
        year        = secici.regex_first(r"\b(19\d{2}|20\d{2})\b", target=secici.select_text("div.text-sm"))

        # Actors parsing fix: Flexible regex for casterslist array
        svelte_script = secici.regex_first(r"<script[^>]*>[\s\S]*?sveltekit[\s\S]*?<\/script>")
        actors        = []
        if svelte_script:
            casters_content = re.search(r"casterslist:(\[.*?\])", svelte_script, re.S)
            if casters_content:
                # Handle unquoted JS keys like name: "..."
                actors = re.findall(r'(?:name|["\']name["\'])\s*:\s*["\'](.*?)["\']', casters_content.group(1))
                actors = list(dict.fromkeys([a.strip() for a in actors if len(a.strip()) > 2]))

        episodes_count = int(secici.regex_first(r'episodesCount"\s*:\s*(\d+)', target=svelte_script) or secici.regex_first(r"episodesCount:(\d+)", target=svelte_script) or 1)
        media_id       = secici.regex_first(r'media"\s*:\s*\{\s*"id"\s*:\s*(\d+)', target=svelte_script) or secici.regex_first(r"media:\{id:(\d+)", target=svelte_script)

        episodes = []
        for i in range(1, episodes_count + 1):
            ep_url    = f"{request_url}/{i}"
            ep_poster = f"https://cdn.animeav1.com/screenshots/{media_id}/{i}.jpg" if media_id else None
            episodes.append(Episode(season=1, episode=i, title=f"Episode {i}", url=ep_url, poster=ep_poster))

        return SeriesInfo(
            url         = request_url,
            poster      = self.fix_url(poster),
            title       = title.strip() if title else "Bilinmeyen",
            description = description,
            tags        = tags,
            year        = str(year) if year else None,
            actors      = actors,
            episodes    = episodes,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek = await self.httpx.get(url)
        text  = istek.text

        embeds_match = re.search(r"embeds:({.*?}),downloads", text, re.S)
        if not embeds_match:
            return []

        embeds_data = embeds_match.group(1)
        response    = []
        tasks       = []

        for lang_type in ["DUB", "SUB"]:
            lang_pattern = rf"{lang_type}:\[(.*?)\]"
            lang_match   = re.search(lang_pattern, embeds_data, re.S)
            if lang_match:
                items = re.findall(r'server:["\']([^"\']+)["\'],url:["\']([^"\']+)["\']', lang_match.group(1))
                for server, video_url in items:
                    if any(x in video_url.lower() for x in ["google", "facebook", "ads", "bio"]):
                        continue
                    tasks.append(self.extract(self.fix_url(video_url), referer=f"{self.main_url}/"))

        # Redirection and mirror discovery
        for iframe in HTMLHelper(text).select("iframe"):
            src = self.fix_url(iframe.attrs.get("data-src") or iframe.attrs.get("src") or "")
            if src and not any(x in src.lower() for x in ["google", "facebook", "ads", "analytics", "data:image"]):
                tasks.append(self.extract(src, referer=url))

        results = await self.gather_with_limit(tasks)
        for res in results:
            self.collect_results(response, res)

        return response
