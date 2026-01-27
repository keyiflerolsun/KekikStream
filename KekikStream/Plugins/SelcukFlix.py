# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
import base64, json, urllib.parse

class SelcukFlix(PluginBase):
    name        = "SelcukFlix"
    lang        = "tr"
    main_url    = "https://selcukflix.net"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Selcukflix'te her türden en yeni ve en popüler dizi ve filmleri izlemenin keyfini çıkarın. Aksiyondan romantiğe, bilim kurgudan dramaya, geniş kütüphanemizde herkes için bir şey var."

    main_page = {
        f"{main_url}/tum-bolumler" : "Yeni Eklenen Bölümler",
        ""                         : "Yeni Diziler",
        ""                         : "Kore Dizileri",
        ""                         : "Yerli Diziler",
        "15"                       : "Aile",
        "17"                       : "Animasyon",
        "9"                        : "Aksiyon",
        "5"                        : "Bilim Kurgu",
        "2"                        : "Dram",
        "12"                       : "Fantastik",
        "18"                       : "Gerilim",
        "3"                        : "Gizem",
        "8"                        : "Korku",
        "4"                        : "Komedi",
        "7"                        : "Romantik"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        results = []
        if "tum-bolumler" in url:
            try:
                resp = await self.httpx.get(url)
                sel  = HTMLHelper(resp.text)

                for item in sel.select("div.col-span-3 a"):
                    name    = sel.select_text("h2", item)
                    ep_info = sel.select_text("div.opacity-80", item)
                    href    = sel.select_attr("a", "href", item)
                    poster  = sel.select_attr("div.image img", "src", item)

                    if name and href:
                        title     = f"{name} - {ep_info}" if ep_info else name
                        final_url = self.fix_url(href)

                        if "/dizi/" in final_url and "/sezon-" in final_url:
                            final_url = final_url.split("/sezon-")[0]

                        results.append(MainPageResult(
                            category = category,
                            title    = title,
                            url      = final_url,
                            poster   = self.fix_url(poster)
                        ))
            except Exception:
                pass
            return results
        
        base_api = f"{self.main_url}/api/bg/findSeries"

        params = {
            "releaseYearStart"   : "1900",
            "releaseYearEnd"     : "2026",
            "imdbPointMin"       : "1",
            "imdbPointMax"       : "10",
            "categoryIdsComma"   : "",
            "countryIdsComma"    : "",
            "orderType"          : "date_desc",
            "languageId"         : "-1",
            "currentPage"        : page,
            "currentPageCount"   : "24",
            "queryStr"           : "",
            "categorySlugsComma" : "",
            "countryCodesComma"  : ""
        }

        if "Yerli Diziler" in category:
            params["imdbPointMin"]    = "5"
            params["countryIdsComma"] = "29"
        elif "Kore Dizileri" in category:
            params["countryIdsComma"]   = "21"
            params["countryCodesComma"] = "KR"
        else:
            params["categoryIdsComma"] = url

        full_url = f"{base_api}?{urllib.parse.urlencode(params)}"

        headers = {
            "User-Agent"       : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
            "Accept"           : "application/json, text/plain, */*",
            "Accept-Language"  : "en-US,en;q=0.5",
            "X-Requested-With" : "XMLHttpRequest",
            "Sec-Fetch-Site"   : "same-origin",
            "Sec-Fetch-Mode"   : "cors",
            "Sec-Fetch-Dest"   : "empty",
            "Referer"          : f"{self.main_url}/"
        }

        try:
            post_resp     = await self.httpx.post(full_url, headers=headers)
            resp_json     = post_resp.json()
            response_data = resp_json.get("response")

            raw_data = base64.b64decode(response_data)
            try:
                decoded_str = raw_data.decode('utf-8')
            except UnicodeDecodeError:
                decoded_str = raw_data.decode('iso-8859-1').encode('utf-8').decode('utf-8')

            data = json.loads(decoded_str)

            for item in data.get("result", []):
                title  = item.get("title")
                slug   = item.get("slug")
                poster = item.get("poster")

                if poster:
                    poster = self.clean_image_url(poster)

                if slug:
                    results.append(MainPageResult(
                        category = category,
                        title    = title,
                        url      = self.fix_url(slug),
                        poster   = poster
                    ))

        except Exception:
            pass

        return results

    async def search(self, query: str) -> list[SearchResult]:
        search_url = f"{self.main_url}/api/bg/searchcontent?searchterm={query}"

        headers = {
            "User-Agent"       : "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
            "Accept"           : "application/json, text/plain, */*",
            "Accept-Language"  : "en-US,en;q=0.5",
            "X-Requested-With" : "XMLHttpRequest",
            "Sec-Fetch-Site"   : "same-origin",
            "Sec-Fetch-Mode"   : "cors",
            "Sec-Fetch-Dest"   : "empty",
            "Referer"          : f"{self.main_url}/"
        }

        post_resp = await self.httpx.post(search_url, headers=headers)

        try:
            resp_json     = post_resp.json()
            response_data = resp_json.get("response")
            raw_data      = base64.b64decode(response_data)
            try:
                decoded_str = raw_data.decode('utf-8')
            except UnicodeDecodeError:
                decoded_str = raw_data.decode('iso-8859-1')

            search_data = json.loads(decoded_str)

            results = []
            for item in search_data.get("result", []):
                # API field isimleri: object_name, used_slug, object_poster_url
                title  = item.get("object_name") or item.get("title")
                slug   = item.get("used_slug") or item.get("slug")
                poster = item.get("object_poster_url") or item.get("poster")

                if poster:
                    poster = self.clean_image_url(poster)

                if slug and "/seri-filmler/" not in slug:
                    results.append(SearchResult(
                        title  = title,
                        url    = self.fix_url(slug),
                        poster = poster
                    ))

            return results

        except Exception:
            return []

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)
        
        next_data_text = sel.select_text("script#__NEXT_DATA__")
        if not next_data_text:
            return SeriesInfo(url=url, title=self.clean_title(sel.select_text("h1")) or "Bilinmeyen")

        try:
            next_data = json.loads(next_data_text)
            secure_data_raw = next_data["props"]["pageProps"].get("secureData")
            if not secure_data_raw:
                  return SeriesInfo(url=url, title=self.clean_title(sel.select_text("h1")) or "Bilinmeyen")
            
            # Clean possible quotes from string before decoding
            if isinstance(secure_data_raw, str):
                secure_data_raw = secure_data_raw.strip('"')

            content_details = json.loads(base64.b64decode(secure_data_raw).decode('utf-8'))
            if isinstance(content_details, str): content_details = json.loads(content_details)

            item            = content_details.get("contentItem", {})
            related_results = content_details.get("RelatedResults", {})

            title       = self.clean_title(item.get("original_title") or item.get("culture_title") or item.get("originalTitle") or "")
            poster      = self.clean_image_url(item.get("poster_url") or item.get("posterUrl") or item.get("face_url"))
            description = item.get("description") or item.get("used_description")
            rating      = str(item.get("imdb_point") or item.get("imdbPoint") or "")
            year        = str(item.get("release_year") or item.get("releaseYear") or "")
            duration    = item.get("total_minutes") or item.get("totalMinutes")

            tags = []
            tags_raw = item.get("category_names") or item.get("categoryNames") or item.get("categories")
            if isinstance(tags_raw, str):
                tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
            elif isinstance(tags_raw, list):
                tags = [c.get("title") if isinstance(c, dict) else str(c) for c in tags_raw]

            actors = []
            casts_data = related_results.get("getSerieCastsById") or related_results.get("getMovieCastsById")
            if casts_data and isinstance(casts_data, dict) and casts_data.get("result"):
                actors = [cast.get("name") for cast in casts_data["result"] if cast.get("name")]

            common_info = {
                "url"         : url,
                "poster"      : poster,
                "title"       : title,
                "description" : description,
                "tags"        : tags,
                "rating"      : rating,
                "year"        : year,
                "actors"      : actors,
                "duration"    : duration
            }

            series_data = related_results.get("getSerieSeasonAndEpisodes")
            if series_data and isinstance(series_data, dict) and series_data.get("result"):
                episodes = []
                for season in series_data["result"]:
                    s_no = season.get("season_no") or season.get("seasonNo") or 1
                    for ep in season.get("episodes", []):
                        ep_slug = ep.get("used_slug") or ep.get("usedSlug")
                        if ep_slug:
                            episodes.append(Episode(
                                season  = s_no,
                                episode = ep.get("episode_no") or ep.get("episodeNo") or 1,
                                title   = ep.get("ep_text") or ep.get("epText") or "",
                                url     = self.fix_url(ep_slug)
                            ))
                return SeriesInfo(**common_info, episodes=episodes)

            return MovieInfo(**common_info)

        except Exception:
            return SeriesInfo(url=url, title=self.clean_title(sel.select_text("h1")) or "Bilinmeyen")

        except Exception:
            return SeriesInfo(url=url, title=self.clean_title(sel.select_text("h1")) or "Bilinmeyen")

    async def load_links(self, url: str) -> list[ExtractResult]:
        resp = await self.httpx.get(url)
        sel  = HTMLHelper(resp.text)
        
        next_data = sel.select_text("script#__NEXT_DATA__")
        if not next_data:
            return []

        try:
            data = json.loads(next_data)
            secure_data = data["props"]["pageProps"]["secureData"]
            raw_data = base64.b64decode(secure_data.replace('"', ''))
            
            try:
                decoded_str = raw_data.decode('utf-8')
            except UnicodeDecodeError:
                decoded_str = raw_data.decode('iso-8859-1')
            
            content_details = json.loads(decoded_str)
            related_results = content_details.get("RelatedResults", {})
            
            source_content = None
            
            # Dizi (bölüm) için
            if "/dizi/" in url:
                episode_sources = related_results.get("getEpisodeSources", {})
                if episode_sources.get("state"):
                    res = episode_sources.get("result", [])
                    if res:
                        source_content = res[0].get("source_content") or res[0].get("sourceContent")
            else:
                # Film için
                movie_parts = related_results.get("getMoviePartsById", {})
                if movie_parts.get("state"):
                    parts = movie_parts.get("result", [])
                    if parts:
                        first_part_id = parts[0].get("id")
                        key = f"getMoviePartSourcesById_{first_part_id}"
                        if key in related_results:
                            res = related_results[key].get("result", [])
                            if res:
                                source_content = res[0].get("source_content") or res[0].get("sourceContent")

            if source_content:
                iframe_sel = HTMLHelper(source_content)
                iframe_src = iframe_sel.select_attr("iframe", "src")
                if iframe_src:
                    iframe_src = self.fix_url(iframe_src)
                    # Hotlinger domain değişimi (Kotlin referansı)
                    if "sn.dplayer74.site" in iframe_src:
                        iframe_src = iframe_src.replace("sn.dplayer74.site", "sn.hotlinger.com")
                    
                    data = await self.extract(iframe_src)
                    if data:
                        return [data]
            
            return []

        except Exception:
            return []

    def clean_image_url(self, url: str) -> str:
        if not url: return None
        url = url.replace("images-macellan-online.cdn.ampproject.org/i/s/", "")
        url = url.replace("file.dizilla.club", "file.macellan.online")
        url = url.replace("images.dizilla.club", "images.macellan.online")
        url = url.replace("images.dizimia4.com", "images.macellan.online")
        url = url.replace("file.dizimia4.com", "file.macellan.online")
        url = url.replace("/f/f/", "/630/910/")
        return self.fix_url(url)
