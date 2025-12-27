# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult
from selectolax.parser import HTMLParser
import re, base64, json, urllib.parse

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
                sel  = HTMLParser(resp.text)

                for item in sel.css("div.col-span-3 a"):
                    name_el   = item.css_first("h2")
                    ep_el     = item.css_first("div.opacity-80")
                    img_el    = item.css_first("div.image img")

                    name    = name_el.text(strip=True) if name_el else None
                    ep_info = ep_el.text(strip=True) if ep_el else None
                    href    = item.attrs.get("href")
                    poster  = img_el.attrs.get("src") if img_el else None

                    if name and href:
                        title     = f"{name} - {ep_info}" if ep_info else name
                        final_url = self.fix_url(href)

                        if "/dizi/" in final_url and "/sezon-" in final_url:
                            final_url = final_url.split("/sezon-")[0]

                        results.append(MainPageResult(
                            category = category,
                            title    = title,
                            url      = final_url,
                            poster   = self.fix_url(poster) if poster else None
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
        sel  = HTMLParser(resp.text)

        next_data_el = sel.css_first("script#__NEXT_DATA__")
        if not next_data_el:
             return None

        next_data = next_data_el.text(strip=True)
        if not next_data: 
             return None

        data         = json.loads(next_data)
        secure_data  = data["props"]["pageProps"]["secureData"]
        raw_data     = base64.b64decode(secure_data.replace('"', ''))
        try:
            decoded_str = raw_data.decode('utf-8')
        except UnicodeDecodeError:
            decoded_str = raw_data.decode('iso-8859-1')

        content_details = json.loads(decoded_str)
        item            = content_details.get("contentItem", {})

        title           = item.get("original_title") or item.get("originalTitle") or ""
        poster          = self.clean_image_url(item.get("poster_url") or item.get("posterUrl"))
        description     = item.get("description") or item.get("used_description")
        rating          = str(item.get("imdb_point") or item.get("imdbPoint", ""))
        year            = item.get("release_year") or item.get("releaseYear")
        duration        = item.get("total_minutes") or item.get("totalMinutes")

        series_data     = content_details.get("relatedData", {}).get("seriesData")
        if not series_data and "RelatedResults" in content_details:
             series_data = content_details["RelatedResults"].get("getSerieSeasonAndEpisodes", {}).get("result")
             if series_data and isinstance(series_data, list):
                  pass

        # Dizi mi film mi kontrol et (Kotlin referansı)
        if series_data:
            episodes = []
            seasons_list = []
            if isinstance(series_data, dict):
                seasons_list = series_data.get("seasons", [])
            elif isinstance(series_data, list):
                seasons_list = series_data

            for season in seasons_list:
                if not isinstance(season, dict): continue
                s_no = season.get("season_no") or season.get("seasonNo")
                ep_list = season.get("episodes", [])
                for ep in ep_list:
                    episodes.append(Episode(
                        season  = s_no,
                        episode = ep.get("episode_no") or ep.get("episodeNo"),
                        title   = ep.get("ep_text") or ep.get("epText"),
                        url     = self.fix_url(ep.get("used_slug") or ep.get("usedSlug"))
                    ))
            
            return SeriesInfo(
                title       = title,
                url         = url,
                poster      = poster,
                description = description,
                rating      = rating,
                year        = year,
                episodes    = episodes
            )
        else:
            # Film ise MovieInfo döndür
            return MovieInfo(
                title       = title,
                url         = url,
                poster      = poster,
                description = description,
                rating      = rating,
                year        = year,
                duration    = duration
            )

    async def load_links(self, url: str) -> list[ExtractResult]:
        resp = await self.httpx.get(url)
        sel  = HTMLParser(resp.text)
        
        next_data_el = sel.css_first("script#__NEXT_DATA__")
        if not next_data_el:
            return []

        next_data = next_data_el.text(strip=True)
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
                iframe_sel = HTMLParser(source_content)
                iframe_el = iframe_sel.css_first("iframe")
                iframe_src = iframe_el.attrs.get("src") if iframe_el else None
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
