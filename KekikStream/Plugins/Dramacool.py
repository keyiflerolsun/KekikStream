# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
from Kekik.Sifreleme  import Packer
import re, base64

class Dramacool(PluginBase):
    name        = "Dramacool"
    language    = "en"
    main_url    = "https://dramacool-l.fun"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Asian Drama Lover, Watch drama asian Online for free releases in Korean, Taiwanese, Thailand, Japanese and Chinese with English subtitles on Dramacool."

    main_page   = {
        f"{main_url}/recently-added-drama" : "Yeni Dizi Bölümleri",
        f"{main_url}/recently-added-kshow" : "Yeni Program Bölümleri",
        f"{main_url}/country/korean"       : "Korean Drama",
        f"{main_url}/country/chinese"      : "Chinese Drama",
        f"{main_url}/country/thailand"     : "Thailand Drama",
        f"{main_url}/country/japanese-a"   : "Japanese Drama",
        f"{main_url}/country/taiwanese"    : "Taiwanese Drama",
        f"{main_url}/country/hong-kong"    : "Hong Kong Drama",
        f"{main_url}/country/american"     : "American Drama",
        f"{main_url}/country/indian"       : "Indian Drama",
        f"{main_url}/country/philippines"  : "Philippines Drama",
    }

    def _convert_to_series_url(self, original_url: str) -> str:
        if "episode-" in original_url:
            parts   = original_url.split("/")
            ep_part = ""
            for p in parts:
                if "episode-" in p:
                    ep_part = p
                    break
            if ep_part:
                series_name = re.sub(r"-episode-\d+.*$", "", ep_part)
                return f"{self.main_url}/series/{series_name}/"
        return original_url

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}/page/{page}")
        secici = HTMLHelper(istek.text)

        results = []
        for li in secici.select("ul.switch-block li"):
            a_tag = li.select_first("a")
            if not a_tag:
                continue

            title  = li.select_text("h3.title")
            href   = a_tag.select_attr(None, "href")
            img    = a_tag.select_first("img")
            poster = (img.select_attr(None, "data-original") or img.select_attr(None, "src")) if img else None

            ep_span = li.select_text("span.ep")

            if "recently-added" in url and ep_span:
                title = f"{title} {ep_span}" if title else ep_span

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title.strip(),
                    url      = self._convert_to_series_url(self.fix_url(href)),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}?type=movies&s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for li in secici.select("ul.switch-block li"):
            a_tag = li.select_first("a")
            if not a_tag:
                continue

            title  = li.select_text("h3.title")
            href   = a_tag.select_attr(None, "href")
            img    = a_tag.select_first("img")
            poster = (img.select_attr(None, "data-original") or img.select_attr(None, "src")) if img else None

            if title and href:
                results.append(SearchResult(
                    title  = title.strip(),
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("div.info h1") or ""
        poster_raw  = secici.select_attr("div.img img", "src")
        poster      = self.fix_url(poster_raw) if poster_raw else ""
        description = ""
        p_elements  = secici.select("div.info > p")
        if len(p_elements) > 2:
            description = p_elements[2].text(strip=True) if hasattr(p_elements[2], "text") else ""

        # selectolax :contains() desteklemez — manuel parse
        year = None
        tags = []
        for p_el in secici.select("div.info p"):
            p_text = p_el.select_text(None) or ""
            if "Released:" in p_text:
                year_a = p_el.select_text("a")
                if year_a:
                    year = year_a.strip()
            elif "Genre:" in p_text:
                tags = p_el.select_texts("a")

        episodes = []
        for li in secici.select("ul.list-episode-item-2.all-episode li"):
            a_tag = li.select_first("a")
            if not a_tag:
                continue

            ep_url = a_tag.select_attr(None, "href")
            if not ep_url:
                continue

            ep_match = re.search(r"episode-(\d+)", ep_url)
            ep_num   = int(ep_match.group(1)) if ep_match else 0

            episodes.append(Episode(
                season  = 1,
                episode = ep_num,
                title   = f"Episode {ep_num}",
                url     = self.fix_url(ep_url),
            ))

        return SeriesInfo(
            url         = url,
            poster      = poster,
            title       = title,
            description = description,
            tags        = tags,
            year        = year,
            episodes    = episodes,
        )

    async def _extract_asianload(self, url: str) -> list[ExtractResult]:
        """AsianLoad JsUnpacker + base64 video çıkarma"""
        results = []
        try:
            resp = await self.httpx.get(url)
            # eval(function(p,a,c,k,e,d) packed JS
            scripts = HTMLHelper(resp.text).select("div#player + script")
            for sc in scripts:
                script_text = sc.text if hasattr(sc, "text") else ""
                if not script_text.startswith("eval(function(p,a,c,k,e,d)"):
                    continue

                unpacked = Packer.unpack(script_text)
                if not unpacked:
                    continue

                # window.atob("...") → base64 decode
                for b64_match in re.finditer(r'window\.atob\("([^"]+)"\)', unpacked):
                    encoded = b64_match.group(1)
                    try:
                        decoded = base64.b64decode(encoded).decode("utf-8")
                        if ".mp4" in decoded or ".m3u8" in decoded:
                            results.append(ExtractResult(
                                name    = "AsianLoad",
                                url     = decoded,
                                referer = url,
                            ))
                    except Exception:
                        pass
        except Exception:
            pass

        return results

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        response = []

        async def _process_iframe(src):
            if "asianload" in src:
                return await self._extract_asianload(src)
            return await self.extract(src, referer=url)

        iframe_srcs = []
        for iframe in secici.select("iframe"):
            src = iframe.select_attr(None, "src")
            if not src:
                continue
            src = src.strip()
            if src.startswith("//"):
                src = f"https:{src}"
            iframe_srcs.append(src)

        tasks = [_process_iframe(src) for src in iframe_srcs]
        for data in await self.gather_with_limit(tasks):
            self.collect_results(response, data)

        # div.watch-iframe iframe fallback
        if not response:
            fallback_srcs = []
            for iframe in secici.select("div.watch-iframe iframe"):
                src = iframe.select_attr(None, "src")
                if not src:
                    continue
                src = src.strip()
                if src.startswith("//"):
                    src = f"https:{src}"
                fallback_srcs.append(src)

            tasks = [self.extract(src, referer=url) for src in fallback_srcs]
            for data in await self.gather_with_limit(tasks):
                self.collect_results(response, data)

        return self.deduplicate(response)
