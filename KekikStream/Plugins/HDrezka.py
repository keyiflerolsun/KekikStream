# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
import base64, re, json, time

class HDrezka(PluginBase):
    name        = "HDrezka"
    language    = "ru"
    main_url    = "https://rezka.ag"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Смотреть фильмы онлайн в HD качестве. Сериалы, мультфильмы, аниме, передачи и ТВ шоу на нашем киносайте, без регистрации и смс. Фильмы в высоком качестве на HDrezka.me"

    main_page   = {
        f"{main_url}/films/?filter=watching"     : "Фильмы",
        f"{main_url}/films/action/?filter=watching" : "Боевики",
        f"{main_url}/films/fiction/?filter=watching" : "Фантастика",
        f"{main_url}/films/comedy/?filter=watching" : "Комедии",
        f"{main_url}/films/thriller/?filter=watching" : "Триллеры",
        f"{main_url}/films/drama/?filter=watching" : "Драмы",
        f"{main_url}/films/horror/?filter=watching" : "Ужасы",
        f"{main_url}/films/detective/?filter=watching" : "Детективы",
        f"{main_url}/films/crime/?filter=watching" : "Криминал",
        f"{main_url}/series/?filter=watching"    : "Сериалы",
        f"{main_url}/series/comedy/?filter=watching" : "Комедийные сериалы",
        f"{main_url}/series/drama/?filter=watching" : "Драматические сериалы",
        f"{main_url}/cartoons/?filter=watching"  : "Мультфильмы",
        f"{main_url}/animation/?filter=watching" : "Аниме",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        parts = url.split("?")
        base  = parts[0]
        query = parts[1] if len(parts) > 1 else ""

        target_url = f"{base}page/{page}/?{query}"
        istek      = await self.httpx.get(target_url)
        secici     = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.b-content__inline_items div.b-content__inline_item"):
            title  = veri.select_text("div.b-content__inline_item-link > a")
            href   = veri.select_attr("a", "href")
            poster = veri.select_poster()

            results.append(MainPageResult(
                category = category,
                title    = title,
                url      = href,
                poster   = poster
            ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        link   = f"{self.main_url}/search/?do=search&subaction=search&q={query}"
        istek  = await self.httpx.get(link)
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.b-content__inline_items div.b-content__inline_item"):
            title  = veri.select_text("div.b-content__inline_item-link > a")
            href   = veri.select_attr("a", "href")
            poster = veri.select_poster()

            results.append(SearchResult(
                title  = title,
                url    = href,
                poster = poster
            ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        doc_id = url.split("/")[-1].split("-")[0]
        title  = secici.select_text("div.b-post__origtitle") or secici.select_text("div.b-post__title h1")
        poster = secici.select_poster("div.b-sidecover img")

        # Metadata
        tags_raw = secici.regex_first(r"Жанр</h2>:</td>\s*<td>(.*?)</td>", flags=re.S)
        tags     = [t.strip() for t in re.sub(r"<[^>]+>", "", tags_raw).split(",")] if tags_raw else []
        year     = secici.regex_first(r"Дата выхода</h2>:</td>\s*<td>.*?(\d{4})")

        description  = secici.select_text("div.b-post__description_text")
        rating       = secici.regex_first(r"IMDb.*?([\d\.]+)")
        actors       = [a.text().strip() for a in secici.select("table.b-post__info > tbody > tr:last-child span.item span[itemprop=name]")]
        duration_raw = secici.regex_first(r"Время.*?<td.*?>(.*?)</td>", flags=re.S)
        duration     = int(re.search(r"(\d+)", duration_raw).group(1)) if duration_raw and re.search(r"(\d+)", duration_raw) else None

        # Extract translators
        translators = []
        t_id        = None

        for li in secici.select("ul#translators-list li"):
            tid = li.attrs.get("data-translator_id")
            if not tid:
                continue

            translators.append({
                "translator_name" : li.text().strip(),
                "translator_id"   : tid,
                "camrip"          : li.attrs.get("data-camrip"),
                "ads"             : li.attrs.get("data-ads"),
                "director"        : li.attrs.get("data-director")
            })

            if not t_id or "active" in li.attrs.get("class", "").split():
                t_id = tid

        # Fallback to regex if no translators found
        t_id = t_id or secici.regex_first(r"data-translator_id=\"(\d+)\"")

        if not translators and t_id:
            translators.append({"translator_name": "Default", "translator_id": t_id})

        data = {
            "id"     : doc_id,
            "favs"   : secici.select_attr("input  #ctrl_favs", "value"),
            "ref"    : url,
            "action" : "get_movie",
            "server" : translators
        }

        # Check if content is series or movie
        is_series = secici.select("div#simple-episodes-tabs") or secici.select("ul#simple-seasons-tabs")

        if is_series:
            episodes = []
            seasons  = secici.select("ul  #simple-seasons-tabs li")
            if seasons:
                for s_li in seasons:
                    s_id   = s_li.attrs.get("data-season_id")
                    s_name = s_li.text().strip()

                    # Extract season number from name if data attribute missing
                    if not s_id:
                        s_id_match = re.search(r"(\d+)", s_name)
                        s_id       = s_id_match.group(1) if s_id_match else "1"

                    # Fetch episodes for this season
                    ep_ajax_url = f"{self.main_url}/ajax/get_cdn_series/?id={doc_id}&translator_id={t_id}&season={s_id}&episode=0&action=get_episodes"
                    ep_istek    = await self.httpx.post(
                        ep_ajax_url,
                        data    = {"id": doc_id, "translator_id": t_id, "season": s_id, "episode": 0, "action": "get_episodes"},
                        headers = {"X-Requested-With": "XMLHttpRequest", "Referer": url}
                    )

                    try:
                        ep_data = ep_istek.json()
                        if ep_data.get("success") and ep_data.get("episodes"):
                            ep_secici = HTMLHelper(ep_data["episodes"])
                            for ep_li in ep_secici.select("li"):
                                ep_id   = ep_li.attrs.get("data-episode_id")
                                ep_name = ep_li.text().strip()

                                ep_url_data = data.copy()
                                ep_url_data.update({
                                    "translator_id" : t_id,
                                    "season"        : s_id,
                                    "episode"       : ep_id,
                                    "action"        : "get_stream"
                                })

                                episodes.append(Episode(
                                    season  = int(s_id) if s_id and s_id.isdigit() else 1,
                                    episode = int(ep_id) if ep_id and ep_id.isdigit() else (len(episodes) + 1),
                                    title   = f"{s_name} - {ep_name}",
                                    url     = json.dumps(ep_url_data)
                                ))
                    except Exception:
                        continue

            if not episodes:
                  ep_url_data = data.copy()
                  ep_url_data["action"] = "get_movie" # Try get_movie for series with only one player
                  episodes.append(Episode(title="Tüm Bölümler / All Episodes", url=json.dumps(ep_url_data)))

            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = title,
                description = description,
                tags        = tags,
                rating      = rating,
                year        = year,
                actors      = actors,
                duration    = duration,
                episodes    = episodes
            )
        else:
            data["action"] = "get_movie"
            return MovieInfo(
                url         = json.dumps(data),
                poster      = poster,
                title       = title,
                description = description,
                tags        = tags,
                rating      = rating,
                year        = year,
                actors      = actors
            )

    def _decrypt_stream_url(self, data: str) -> str:
        trash_chars = ["@", "#", "!", "^", "$"]

        # Generate all 2 and 3 character combinations
        trash_patterns = [
            t1 + t2 + t3 for t1 in trash_chars for t2 in trash_chars for t3 in trash_chars
        ] + [
            t1 + t2 for t1 in trash_chars for t2 in trash_chars
        ]

        # Clean and decode
        cleaned = "".join(data.replace("#h", "").split("//_//"))
        for pattern in trash_patterns:
            cleaned = cleaned.replace(base64.b64encode(pattern.encode()).decode(), "")

        try:
            return base64.b64decode(cleaned).decode()
        except Exception:
            return ""

    async def load_links(self, url: str) -> list[ExtractResult]:
        try:
            res = json.loads(url)
        except Exception:
            # Fallback for direct URLs
            return [ExtractResult(name=self.name, url=url)]

        results = []

        if not res.get("server"):
            # Local Movie Link
            istek  = await self.httpx.get(res["ref"])
            secici = HTMLHelper(istek.text)

            # Look for script data
            script_match = re.search(r"sof\.tv\.initCDNMoviesEvents\(.+?false,\s*({.+?})\);", istek.text, re.DOTALL)
            if script_match:
                try:
                    source_data = json.loads(script_match.group(1))
                    streams     = source_data.get("streams", "")
                    results.extend(self._invoke_sources(self.name, streams))
                except Exception:
                    pass

            # Fallback for series if script missing or stream not found
            if not results and res.get("id"):
                # Try all possible actions for series placeholders
                for action in ["get_episodes", "get_stream", "get_movie"]:
                    t_id = res.get("translator_id") or secici.regex_first(r"data-translator_id=\"(\d+)\"")
                    if t_id:
                        payload = {
                            "id"            : res["id"],
                            "translator_id" : t_id,
                            "favs"          : res.get("favs"),
                            "action"        : action
                        }
                        if res.get("season"):
                            payload["season"] = res["season"]
                        if res.get("episode"):
                            payload["episode"] = res["episode"]

                        api_url = f"{self.main_url}/ajax/get_cdn_series/"
                        istek_api = await self.httpx.post(api_url, data=payload, headers={"Referer": res["ref"], "X-Requested-With": "XMLHttpRequest"})
                        try:
                            api_data = istek_api.json()
                            if api_data.get("url"):
                                results.extend(self._invoke_sources("Default", api_data["url"]))
                                if results:
                                    break
                            elif api_data.get("episodes") and action == "get_episodes":
                                # If we got episodes list, try to get the first one's stream
                                ep_secici   = HTMLHelper(api_data["episodes"])
                                first_ep_li = ep_secici.select_first("li")
                                if first_ep_li:
                                    f_ep_id = first_ep_li.attrs.get("data-episode_id")
                                    f_s_id  = first_ep_li.attrs.get("data-season_id") or res.get("season") or "1"
                                    # Recursive-ish call for the first episode
                                    payload.update({"action": "get_stream", "season": f_s_id, "episode": f_ep_id})
                                    istek_f = await self.httpx.post(api_url, data=payload, headers={"Referer": res["ref"], "X-Requested-With": "XMLHttpRequest"})
                                    f_data = istek_f.json()
                                    if f_data.get("url"):
                                        results.extend(self._invoke_sources("Default", f_data["url"]))
                                        if results:
                                            break
                        except Exception:
                            pass
        else:
            # Series or Translatable Movie
            for server in res["server"]:
                payload = {
                    "id"            : res["id"],
                    "translator_id" : server["translator_id"],
                    "favs"          : res["favs"],
                    "is_camrip"     : server.get("camrip", "0"),
                    "is_ads"        : server.get("ads", "0"),
                    "is_director"   : server.get("director", "0"),
                    "action"        : res["action"]
                }

                if "season" in res:
                    payload["season"] = res["season"]
                if "episode" in res:
                    payload["episode"] = res["episode"]

                # Remove None values
                payload = {k: v for k, v in payload.items() if v is not None}

                timestamp = int(time.time() * 1000)
                api_url   = f"{self.main_url}/ajax/get_cdn_series/?t={timestamp}"
                istek     = await self.httpx.post(api_url, data=payload, headers={"Referer": res["ref"], "X-Requested-With": "XMLHttpRequest"})

                try:
                    data = istek.json()
                    if data.get("url"):
                        results.extend(self._invoke_sources(server["translator_name"], data["url"]))
                except Exception:
                    continue

        return results

    def _invoke_sources(self, source_name: str, encrypted_url: str) -> list[ExtractResult]:
        decrypted = self._decrypt_stream_url(encrypted_url)
        if not decrypted:
            return []

        results = []
        # Format: [720p]https://... or [1080p]https://...
        # Split by comma
        for part in decrypted.split(","):
            match = re.search(r"\[(\d+p.*?)\](.*)", part)
            if match:
                quality = match.group(1)
                links   = match.group(2).split(" or ")
                for link in links:
                    link = link.strip()
                    if not link: continue

                    label = f"{source_name} | {quality}"
                    if ".m3u8" in link:
                        label += " (Main)"
                    else:
                        label += " (Backup)"

                    results.append(ExtractResult(
                        name    = label,
                        url     = link,
                        referer = f"{self.main_url}/"
                    ))
        return results
