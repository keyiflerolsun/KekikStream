# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re


class JPFilms(PluginBase):
    name        = "JPFilms"
    language    = "en"
    main_url    = "https://jp-films.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Watch online The Legend of Love & Sincerity on Japanese Classic Movies and TVSeries (https://jp-films.com) with English Subtitle. Japanese Classic Movies, Japanese Classic TVSeries, Jindaigeki, Action, Tora-san, Zatoichi"

    main_page = {
        f"{main_url}/tag/akira-kurosawa"                 : "Akira Kurosawa",
        f"{main_url}/tag/godzilla-collection"            : "Godzilla",
        f"{main_url}/tag/ninja-vixens-series"            : "Ninja Vixens",
        f"{main_url}/tag/tora-san"                       : "Tora-san",
        f"{main_url}/tag/zatoichi"                       : "Zatoichi",
        f"{main_url}/tag/criterion-collection"           : "Criterion Collection",
        f"{main_url}/tag/the-hoodlum-soldier-collection" : "The Hoodlum Soldier",
        f"{main_url}/tag/top-imdb"                       : "Top IMDb",
        f"{main_url}/tv-series/"                         : "Latest Series",
        f"{main_url}/movies/"                            : "Latest Movies",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        full_url = url if page <= 1 else f"{url.rstrip('/')}/page/{page}/"
        istek    = await self.httpx.get(full_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for item in secici.select("article.thumb.grid-item"):
            link   = item.select_first("a.halim-thumb")
            title  = item.select_text("h2.entry-title")
            href   = link.attrs.get("href") if link else None
            poster = item.select_poster("img")

            if title and href:
                results.append(MainPageResult(category=category, title=title.strip(), url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        full_url = f"{self.main_url}/search/{query}"
        istek    = await self.httpx.get(full_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for item in secici.select("article.thumb.grid-item"):
            link   = item.select_first("a.halim-thumb")
            title  = item.select_text("h2.entry-title")
            href   = link.attrs.get("href") if link else None
            poster = item.select_poster("img")

            if title and href:
                results.append(SearchResult(title=title.strip(), url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        raw_title   = secici.select_text("h1.entry-title")
        title       = re.sub(r"\s*\(\d{4}\)$", "", raw_title) if raw_title else "Bilinmeyen"
        poster      = secici.select_attr(".movie-thumb img", "src") or secici.select_attr("meta[property='og:image']", "content")
        description = secici.select_text("article.item-content")

        # Meta verileri
        year   = secici.extract_year(".released a[href*='release']")
        tags   = secici.select_texts(".category a")
        rating = secici.select_text(".halim_imdbrating .score")
        actors = secici.select_texts(".actors a")

        episodes = []
        # Hem dizi bölümlerini hem de tekli film linklerini yakala
        items = secici.select(".halim-list-eps li, .halim-watch-box a.watch-movie")

        seen_urls = set()
        for item in items:
            link = item.select_first("a") or item
            span = item.select_first("span")
            href = self.fix_url(link.attrs.get("href") or (span.attrs.get("data-href") if span else None))
            name = (span.text(strip=True) if span else link.text(strip=True)) or "Watch"

            if href and href not in seen_urls:
                seen_urls.add(href)
                num_match = re.search(r"(\d+)", name)
                ep_num    = int(num_match.group(1)) if num_match else len(episodes) + 1

                episodes.append(Episode(season=1, episode=ep_num, title=name, url=href))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title.strip(),
            description = description,
            tags        = tags,
            year        = str(year) if year else None,
            rating      = rating,
            actors      = actors,
            episodes    = episodes,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        episodes = []

        # 1. jsonEpisodes'ı dene
        eps_match = re.search(r'var jsonEpisodes\s*=\s*(\[\[.+?\]\])(?:;|</script>)', istek.text, re.DOTALL)
        if eps_match:
            try:
                import json
                eps_data = json.loads(eps_match.group(1))

                # Aktif olan bölümün indeksini bul
                active_idx = -1
                for server_list in eps_data:
                    for idx, ep in enumerate(server_list):
                        if "active" in (ep.get("activeItem") or ""):
                            active_idx = idx
                            break
                    if active_idx != -1:
                        break

                if active_idx == -1:
                    active_idx = 0

                # Sadece bu indeksteki sunucu alternatiflerini topla
                for server_list in eps_data:
                    if 0 <= active_idx < len(server_list):
                        ep = server_list[active_idx]
                        episodes.append({
                            "slug"      : ep.get("episodeSlug"),
                            "server_id" : ep.get("serverId"),
                            "post_id"   : ep.get("postId"),
                            "name"      : ep.get("episodeName", "").strip() or "Server"
                        })
            except:
                pass

        # 2. Butonları dene (yedek olarak)
        if not episodes:
            buttons     = secici.select(".halim-list-eps .halim-btn")
            active_slug = None
            for btn in buttons:
                if "active" in btn.attrs.get("class", []):
                    active_slug = btn.attrs.get("data-episode-slug")
                    break
            if not active_slug:
                active_slug = url.split("/")[-1].replace(".html", "")
                if "-sv" in active_slug:
                    active_slug = active_slug.split("-sv")[0]

            for btn in buttons:
                slug      = btn.attrs.get("data-episode-slug")
                server_id = btn.attrs.get("data-server")
                post_id   = btn.attrs.get("data-post-id")
                name      = btn.text(strip=True) or "Server"
                if slug and server_id and post_id:
                    clean_slug   = slug.split("-sv")[0] if "-sv" in slug else slug
                    clean_active = active_slug.split("-sv")[0] if "-sv" in active_slug else active_slug
                    if clean_slug == clean_active or len(buttons) <= 4:
                        episodes.append({
                            "slug"      : slug,
                            "server_id" : server_id,
                            "post_id"   : post_id,
                            "name"      : name
                        })

        # 3. halim_cfg'yi dene (ikinci yedek olarak)
        if not episodes:
            cfg_match = re.search(r'var halim_cfg\s*=\s*({.+?})(?:;|</script>)', istek.text, re.DOTALL)
            if cfg_match:
                try:
                    import json
                    cfg       = json.loads(cfg_match.group(1))
                    slug      = cfg.get("episode_slug")
                    server_id = cfg.get("server")
                    post_id   = cfg.get("post_id")
                    if slug and server_id and post_id:
                        episodes.append({
                            "slug"      : slug,
                            "server_id" : server_id,
                            "post_id"   : post_id,
                            "name"      : "Server"
                        })
                except:
                    pass

        response = []
        tasks    = []

        # Sayfadaki alternatif alt sunucuları (subsv_id) topla
        subsv_ids = [""]
        spans     = re.findall(r'data-subsv-id=["\']([^"\']+)["\']', istek.text, re.IGNORECASE)
        for s_id in spans:
            if s_id not in subsv_ids:
                subsv_ids.append(s_id)

        async def fetch_source(slug, server_id, post_id, name, subsv_id) -> list[ExtractResult]:
            ajax_url    = f"{self.main_url}/wp-content/themes/halimmovies/player.php"
            found_links = []
            try:
                resp = await self.httpx.get(
                    ajax_url,
                    params  = {
                        "episode_slug" : slug,
                        "server_id"    : server_id,
                        "post_id"      : post_id,
                        "subsv_id"     : subsv_id
                    },
                    headers = {"X-Requested-With": "XMLHttpRequest", "Referer": url},
                )
                if resp.status_code == 200:
                    html = resp.text

                    # A. VIDEO_SRC kontrolü
                    src_match = re.search(r'VIDEO_SRC\s*=\s*"([^"]+)"', html)
                    if not src_match:
                        src_match = re.search(r'VIDEO_SRC\s*=\s*\'([^\']+)\'', html)
                    if src_match:
                        m3u8_url = src_match.group(1).replace("\\/", "/")
                        found_links.append(ExtractResult(
                            name       = f"{self.name} - {name}",
                            url        = self.fix_url(m3u8_url),
                            referer    = url,
                            user_agent = self.httpx.headers.get("User-Agent")
                        ))

                    # B. HYDRAX_ID kontrolü
                    hydrax_match = re.search(r'HYDRAX_ID\s*=\s*"([^"]+)"', html)
                    if not hydrax_match:
                        hydrax_match = re.search(r'HYDRAX_ID\s*=\s*\'([^\']+)\'', html)
                    if hydrax_match:
                        hydrax_id = hydrax_match.group(1)
                        found_links.append(ExtractResult(
                            name       = f"{self.name} - {name} (Hydrax)",
                            url        = f"https://short.icu/{hydrax_id}",
                            referer    = url,
                            user_agent = self.httpx.headers.get("User-Agent")
                        ))

                    # C. iframe kontrolü (402.html hariç)
                    sec        = HTMLHelper(html)
                    iframe_src = sec.select_attr("iframe", "src")
                    if iframe_src and "402.html" not in iframe_src:
                        found_links.append(ExtractResult(
                            name       = f"{self.name} - {name}",
                            url        = self.fix_url(iframe_src),
                            referer    = url,
                            user_agent = self.httpx.headers.get("User-Agent")
                        ))
            except:
                pass
            return found_links

        for ep in episodes:
            slug      = ep["slug"]
            server_id = ep["server_id"]
            post_id   = ep["post_id"]
            name      = ep["name"]
            for subsv_id in subsv_ids:
                tasks.append(fetch_source(slug, server_id, post_id, name, subsv_id))

        results = await self.gather_with_limit(tasks)
        for res_list in results:
            if res_list:
                response.extend(res_list)

        return response
