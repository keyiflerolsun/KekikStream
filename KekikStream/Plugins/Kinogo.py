# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re, json, base64, asyncio

class Kinogo(PluginBase):
    name        = "Kinogo"
    language    = "ru"
    main_url    = "https://kinogo.online"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Смотреть фильмы и сериалы онлайн бесплатно на официальном КИНОГО в хорошем качестве."

    main_page   = {
        f"{main_url}/filmy/page/"           : "Все фильмы",
        f"{main_url}/serialy/page/"         : "Сериалы",
        f"{main_url}/multfilmy/page/"       : "Мультфильмы",
        f"{main_url}/anime/page/"           : "Аниме",
        f"{main_url}/tv-peredachi/page/"    : "ТВ Передачи",
        f"{main_url}/pod-borki/page/"       : "Подборки",
        f"{main_url}/novinki/page/"         : "Новинки",
        f"{main_url}/fantastika/page/"      : "Фантастика",
        f"{main_url}/fjentezi/page/"        : "Фэнтези",
        f"{main_url}/nuar/page/"            : "Нуар",
        f"{main_url}/uzhasy/page/"          : "Ужасы",
        f"{main_url}/triller/page/"         : "Триллер",
        f"{main_url}/sport/page/"           : "Спорт",
        f"{main_url}/prikljuchenija/page/"  : "Приключения",
        f"{main_url}/istoricheskie/page/"   : "Исторические",
        f"{main_url}/mjuzikl/page/"         : "Мюзикл",
        f"{main_url}/melodrama/page/"       : "Мелодрама",
        f"{main_url}/korotkometrazhka/page/": "Короткометражка",
        f"{main_url}/kriminal/page/"        : "Криминал",
        f"{main_url}/drama/page/"           : "Драма",
        f"{main_url}/komedija/page/"        : "Комедия",
        f"{main_url}/dokumentalnye/page/"   : "Документальные",
        f"{main_url}/detektiv/page/"        : "Детектив",
        f"{main_url}/detskij/page/"         : "Детский",
        f"{main_url}/voennyj/page/"         : "Военный",
        f"{main_url}/vestern/page/"         : "Вестерн",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.async_cf_get(f"{url}{page}/")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select(".shortStory"):
            title = veri.select_attr("a", "title") or veri.select_attr("img", "alt")
            href  = veri.select_attr("a", "href")
            img   = veri.select_poster("img")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(img),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.async_cf_get(f"{self.main_url}/index.php?do=search&subaction=search&story={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select(".shortStory"):
            title = veri.select_attr("a", "title") or veri.select_attr("img", "alt")
            href  = veri.select_attr("a", "href")
            img   = veri.select_poster("img")

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(img),
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        poster      = self.fix_url(secici.select_poster("div.sPoster img") or secici.select_poster("div.fullstoryPoster img") or secici.select_poster("div.fposter img") or secici.select_attr("meta[property='og:image']", "content"))
        description = secici.select_attr("meta[property='og:description']", "content")
        title       = secici.select_text("h1")

        year         = secici.meta_value("Год выпуска") or secici.meta_value("Год")
        rating       = secici.meta_value("IMDB") or secici.meta_value("КиноПоиск")
        duration_raw = secici.meta_value("Продолжительность")
        if duration_raw:
            parts = duration_raw.split()
            duration = int(parts[0]) if parts[0].isdigit() else None
        else:
            duration = None

        tags   = secici.meta_list("Жанр")
        actors = secici.meta_list("Актеры") or secici.meta_list("В ролях")

        iframes = []
        for i_src in secici.select_attrs("iframe", "src") + secici.select_attrs("iframe", "data-src"):
            if i_src and "youtube" not in i_src and "facebook" not in i_src and "vk.com" not in i_src:
                iframes.append(i_src)

        for p_src in secici.select_attrs("li", "data-src"):
            if p_src and "youtube" not in p_src and "facebook" not in p_src and "vk.com" not in p_src:
                iframes.append(p_src)

        if not iframes:
            i = secici.regex_first(r'<iframe[^>]+src=[\"\']([^\"\']+)[\"\']')
            if i and "youtube" not in i and "facebook" not in i and "vk.com" not in i:
                iframes.append(i)

        iframes  = list(set([self.fix_url(i) for i in iframes]))
        episodes = []

        if iframes:
            for iframe in iframes:
                playlist = await self._get_alloha_playlist(iframe, url)
                if playlist:
                    for ep_data in playlist:
                        if ep_data.get("type") == "series":
                            s_num = ep_data["season"]
                            e_num = ep_data["episode"]
                            episodes.append(Episode(
                                season  = s_num,
                                episode = e_num,
                                title   = f"Серия {e_num}",
                                url     = f"{url}#season={s_num}&episode={e_num}"
                            ))
                    if episodes:
                        break

        if episodes:
            return SeriesInfo(
                url         = url,
                poster      = poster,
                title       = title,
                description = description,
                tags        = tags,
                rating      = rating,
                year        = year,
                duration    = duration,
                actors      = actors,
                episodes    = episodes
            )

        return MovieInfo(
            url         = url,
            poster      = poster,
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            duration    = duration,
            actors      = actors
        )

    async def _get_alloha_playlist(self, iframe_url: str, referer: str) -> list[dict]:
        try:
            req    = await self.async_cf_get(iframe_url, headers={"Referer": referer})
            i_text = req.text

            match  = re.search(r'\"file\"\:\"(.*?)\"', i_text)
            if not match:
                return []

            encoded = match.group(1).replace('//_//', '')

            if encoded.startswith('#2'):
                e  = encoded[2:]
                dm = e[0:2]
                try:
                    delim = chr(int(dm))
                except Exception:
                    delim = '#'

                parts  = e[2:].split(delim)
                result = []
                ml     = 32

                for p in parts:
                    if not p:
                        continue
                    try:
                        t = int(p[-1])
                        if len(p) > ml:
                            result.append(p[2*t : 2*t + len(p) - 3*t - 1] + p[0:t])
                        else:
                            result.append(p)
                    except Exception:
                        result.append(p)
                encoded = "".join(result)

            idx = encoded.find('W3s')
            if idx == -1:
                idx = encoded.find('eyJ')
            if idx == -1:
                return []

            b64 = encoded[idx:]
            b64 = re.sub(r'[^A-Za-z0-9+/=_\-]', '', b64)
            b64 += '=' * ((4 - len(b64) % 4) % 4)

            raw = base64.b64decode(b64).decode('utf-8', errors='ignore')

            try:
                data = json.loads(raw)
            except Exception:
                return []

            playlist = []

            # Handle parsing differently based on whether it is a Series or a Movie
            for item in data:
                if "folder" in item:
                    # It's a Series Season
                    s_match = re.search(r's(\d+)', item.get("id", ""))
                    s_num   = int(s_match.group(1)) if s_match else 1
                    for ep in item["folder"]:
                        e_match = re.search(r'e(\d+)', ep.get("id", ""))
                        e_num   = int(e_match.group(1)) if e_match else 1

                        voices = []
                        if "folder" in ep:
                            # Sometimes voices are nested in folders
                            for v in ep["folder"]:
                                voices.append({"title": v.get("title", "Unknown"), "link": self.fix_url(v.get("file", ""))})
                        else:
                            voices.append({"title": item.get("title", ""), "link": self.fix_url(ep.get("file", ""))})

                        playlist.append({
                            "type"    : "series",
                            "season"  : s_num,
                            "episode" : e_num,
                            "voices"  : voices
                        })
                elif "file" in item:
                    # It's a Movie
                    playlist.append({
                        "type"  : "movie",
                        "title" : item.get("title", ""),
                        "link"  : self.fix_url(item.get("file", ""))
                    })

            return playlist
        except Exception as e:
            return []

    async def _get_kodik_links(self, iframe_url: str, referer: str) -> list[dict]:
        try:
            req = await self.async_cf_get(iframe_url, headers={'Referer': referer})

            v_type_match = re.search(r"vInfo\.type\s*=\s*'([^']+)'", req.text)
            if not v_type_match:
                return []

            v_type = v_type_match.group(1)
            v_hash = re.search(r"vInfo\.hash\s*=\s*'([^']+)'", req.text).group(1)
            v_id   = re.search(r"vInfo\.id\s*=\s*'([^']+)'", req.text).group(1)

            d_sign, pd_sign, ref_sign = None, None, None
            try:
                d_sign   = re.search(r"var d_sign\s*=\s*\"([^\"]+)\"", req.text).group(1)
                pd_sign  = re.search(r"var pd_sign\s*=\s*\"([^\"]+)\"", req.text).group(1)
                ref_sign = re.search(r"var ref_sign\s*=\s*\"([^\"]+)\"", req.text).group(1)
            except AttributeError:
                params_match = re.search(r"var urlParams\s*=\s*'([^']+)'", req.text)
                if params_match:
                    jsn      = json.loads(params_match.group(1))
                    d_sign   = jsn.get('d_sign')
                    pd_sign  = jsn.get('pd_sign')
                    ref_sign = jsn.get('ref_sign')

            if not all([d_sign, pd_sign, ref_sign]):
                return []

            api_url = "https://kodik.info/ftor"
            d_match = re.search(r"var domain\s*=\s*\"([^\"]+)\"", req.text)
            domain  = d_match.group(1) if d_match else "kinogo.online"

            data = {
                "d"              : domain,
                "d_sign"         : d_sign,
                "pd"             : "kodik.info",
                "pd_sign"        : pd_sign,
                "ref"            : referer,
                "ref_sign"       : ref_sign,
                "bad_user"       : "true",
                "cdn_is_working" : "true",
                "type"           : v_type,
                "hash"           : v_hash,
                "id"             : v_id,
                "info"           : "{}"
            }
            headers = {
                'Accept'           : 'application/json, text/javascript, */*; q=0.01',
                'Content-Type'     : 'application/x-www-form-urlencoded; charset=UTF-8',
                'Origin'           : 'https://kodik.info',
                'Referer'          : iframe_url,
                'X-Requested-With' : 'XMLHttpRequest',
                'User-Agent'       : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
            }

            api_req   = await self.async_cf_post(api_url, data=data, headers=headers)
            resp_json = api_req.json()

            def decode_kodik(hash_str):
                res = ''
                for char in hash_str:
                    if char.isalpha():
                        start = ord('a') if char.islower() else ord('A')
                        res += chr(start + (ord(char) - start + 18) % 26)
                    else:
                        res += char
                res += '=' * ((4 - len(res) % 4) % 4)
                try:
                    decoded = base64.b64decode(res).decode('utf-8', errors='strict')
                    url     = decoded
                    # url = decoded.replace(':hls:manifest.m3u8', '')
                    if url.startswith('//'):
                        url = 'https:' + url

                    return url
                except Exception:
                    return None

            links   = resp_json.get("links", {})
            results = []
            for resolution, hashes in links.items():
                if isinstance(hashes, list) and len(hashes) > 0:
                    encoded_src = hashes[0].get("src")
                    if encoded_src:
                        decoded = decode_kodik(encoded_src)
                        if decoded:
                            results.append({
                                "resolution" : resolution,
                                "link"       : decoded
                            })
            return results
        except Exception:
            return []

    async def load_links(self, url: str) -> list[ExtractResult]:
        target_season  = None
        target_episode = None

        if "#season=" in url:
            parts    = url.split("#season=")
            real_url = parts[0]
            se_parts = parts[1].split("&episode=")
            if len(se_parts) == 2:
                target_season  = int(se_parts[0])
                target_episode = int(se_parts[1])

            url = real_url

        istek  = await self.async_cf_get(url)
        secici = HTMLHelper(istek.text)

        iframes = []
        for i_src in secici.select_attrs("iframe", "src") + secici.select_attrs("iframe", "data-src"):
            if i_src and "youtube" not in i_src and "facebook" not in i_src and "vk.com" not in i_src:
                iframes.append(i_src)

        for p_src in secici.select_attrs("li", "data-src"):
            if p_src and "youtube" not in p_src and "facebook" not in p_src and "vk.com" not in p_src:
                iframes.append(p_src)

        if not iframes:
            i = secici.regex_first(r'<iframe[^>]+src=[\"\']([^\"\']+)[\"\']')
            if i and "youtube" not in i and "facebook" not in i and "vk.com" not in i:
                iframes.append(i)

        iframes = list(set([self.fix_url(i) for i in iframes]))
        results = []

        if target_season is not None and target_episode is not None and iframes:
            for iframe in iframes:
                playlist = await self._get_alloha_playlist(iframe, url)
                for ep_data in playlist:
                    if ep_data.get("type") == "series" and ep_data["season"] == target_season and ep_data["episode"] == target_episode:
                        for v in ep_data["voices"]:
                            clean_title = re.sub(r'<[^>]+>', '', v['title']).strip()
                            results.append(ExtractResult(
                                name    = clean_title if clean_title else "Kinogo",
                                url     = self.fix_url(v['link']),
                                referer = self.main_url
                            ))
                if results:
                    break
            return results

        if not iframes:
            return []

        # Movie parsing payload extraction
        extract_iframes = []
        for iframe in iframes:
            if any(x in iframe for x in ["cinemar", "fotpro", "alloha"]):
                playlist = await self._get_alloha_playlist(iframe, url)
                for item in playlist:
                    if item.get("type") == "movie":
                        clean_title = re.sub(r'<[^>]+>', '', item.get('title', '')).strip()
                        m_name      = clean_title if clean_title else "Kinogo"
                        results.append(ExtractResult(
                            name    = m_name,
                            url     = self.fix_url(item['link']),
                            referer = self.main_url
                        ))
            elif "api.variyt.ws" in iframe:
                v_req = await self.async_cf_get(iframe, headers={"Referer": url})
                v_match = re.search(r'source\:\s*\{\s*hls\:\s*\"(.*?)\"', v_req.text)
                if v_match:
                    results.append(ExtractResult(
                        name    = "Variyt",
                        url     = self.fix_url(v_match.group(1).replace('\\/', '/')),
                        referer = self.main_url
                    ))
            elif "kodik.info" in iframe:
                kodik_links = await self._get_kodik_links(iframe, url)
                for kl in kodik_links:
                    results.append(ExtractResult(
                        name    = f"Kodik {kl['resolution']}p",
                        url     = self.fix_url(kl['link']),
                        referer = self.main_url
                    ))
            else:
                extract_iframes.append(iframe)

        # External extractors for remaining iframes
        if extract_iframes:
            tasks          = [self.extract(self.fix_url(i)) for i in extract_iframes]
            extracted_data = await asyncio.gather(*tasks)

            for i, data in enumerate(extracted_data):
                if data:
                    self.collect_results(results, data)

        return results
