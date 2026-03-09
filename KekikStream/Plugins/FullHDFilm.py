# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit
import base64, re

class FullHDFilm(PluginBase):
    name        = "FullHDFilm"
    language    = "tr"
    main_url    = "https://fullhdfilm.cx"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Fullhdfilm ile en yeni vizyon filmler Full HD ve kesintisiz film sizlerle. Özgün film arşivimizle en üstün kaliteli film izle keyfini sunuyoruz."

    main_page   = {
        f"{main_url}/yabanci-dizi-izle/page"          : "Yabancı Dizi",
        f"{main_url}/yabanci-film-izle/page"           : "Yabancı Film",
        f"{main_url}/yerli-film-izle/page"             : "Yerli Film",
        f"{main_url}/netflix-filmleri-izle/page"       : "Netflix",
        f"{main_url}/aile-filmleri/page"               : "Aile",
        f"{main_url}/aksiyon-filmleri-izle-hd1/page"   : "Aksiyon",
        f"{main_url}/animasyon-filmleri-izlesene/page"  : "Animasyon",
        f"{main_url}/bilim-kurgu-filmleri/page"        : "Bilim Kurgu",
        f"{main_url}/dram-filmleri/page"               : "Dram",
        f"{main_url}/fantastik-filmler-izle/page"      : "Fantastik",
        f"{main_url}/gerilim-filmleri-izle-hd/page"    : "Gerilim",
        f"{main_url}/gizem-filmleri/page"              : "Gizem",
        f"{main_url}/komedi-filmleri/page"             : "Komedi",
        f"{main_url}/korku-filmleri-izle/page"         : "Korku",
        f"{main_url}/macera-filmleri-izle-hd/page"     : "Macera",
        f"{main_url}/romantik-filmler/page"            : "Romantik",
        f"{main_url}/savas-filmleri-izle-hd/page"      : "Savaş",
        f"{main_url}/suc-filmleri-izle/page"           : "Suç",
    }

    @staticmethod
    def _iframe_coz(veri: str) -> str:
        """IframeKodlayici — Base64 obfuscated iframe decode."""
        if not veri:
            return ""
        # Kotlin: tersCevir("BSZtFmcmlGP") = "PGlmcmFtZSB"
        if not veri.startswith("PGltZyB3aWR0aD0iMTAwJSIgaGVpZ2"):
            veri = "BSZtFmcmlGP"[::-1] + veri  # "PGlmcmFtZSB" + veri
        try:
            decoded = base64.b64decode(veri).decode("utf-8")
            match   = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', decoded)
            return match.group(1) if match else ""
        except Exception:
            return ""

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}/{page}/")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movie_box"):
            title  = veri.select_text("h2")
            href   = veri.select_attr("a", "href")
            poster = veri.select_attr("img", "data-src")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/arama/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movie_box"):
            title  = veri.select_text("h2")
            href   = veri.select_attr("a", "href")
            poster = veri.select_attr("img", "data-src")

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("h1 span")
        poster      = secici.select_attr("[property='og:image']", "content")
        raw_desc    = secici.select_text("div[itemprop='description']") or ""
        description = raw_desc.split("konusu:")[-1].strip() if "konusu:" in raw_desc else raw_desc.split("izleyin.")[-1].strip()
        year        = secici.select_text("span[itemprop='dateCreated'] a")
        tags        = secici.select_texts("div.detail ul.bottom li:nth-child(5) span a")
        rating      = secici.select_text("ul.right li:nth-child(2) span")
        duration    = secici.regex_first(r"(\d+)", secici.select_text("span[itemprop='duration']"))
        actors      = secici.select_texts("sc[itemprop='actor'] span")

        is_series = "-dizi" in url.lower() or any("dizi" in t.lower() for t in tags)

        if is_series:
            episodes   = []
            pdata_list = re.findall(r"pdata\['(.*?)'\]\s*=\s*'(.*?)';", istek.text)

            part_ids   = [el.attrs.get("id", "") for el in secici.select("li.psec")]
            part_names = [el.text(strip=True) for el in secici.select("li.psec a")]

            for idx, (key, value) in enumerate(pdata_list):
                part_name = part_names[idx] if idx < len(part_names) else ""
                if "fragman" in part_name.lower() or "fragman" in key.lower():
                    continue

                iframe_url = self._iframe_coz(value)
                if not iframe_url:
                    continue

                iframe_url = self.fix_url(iframe_url)

                sz_num = 1
                ep_num = idx + 1
                if "sezon" in key:
                    sz_match = re.search(r"(\d+)sezon", key)
                    if sz_match:
                        sz_num   = int(sz_match.group(1))
                ep_match = re.match(r"(\d+)", part_name)
                if ep_match:
                    ep_num = int(ep_match.group(1))

                episodes.append(Episode(
                    season  = sz_num,
                    episode = ep_num,
                    title   = f"{sz_num}. Sezon {ep_num}. Bölüm",
                    url     = self._with_query(url, {"part": str(idx)}),
                ))

            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = title,
                description = description,
                tags        = tags,
                year        = year,
                actors      = actors,
                rating      = rating,
                duration    = duration,
                episodes    = episodes,
            )

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            year        = year,
            actors      = actors,
            rating      = rating,
            duration    = duration,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        response = []

        # Dizi bölüm — URL doğrudan iframe linki (load_item'dan)
        if self.main_url not in url:
            data = await self.extract(url, referer=f"{self.main_url}/")
            self.collect_results(response, data)
            return response

        # Film — pdata[] iframe'lerini çöz
        selected_part = parse_qs(urlsplit(url).query).get("part", [""])[0]
        base_url      = urlsplit(url)._replace(query="").geturl()

        istek      = await self.httpx.get(base_url)
        pdata_list = re.findall(r"pdata\['(.*?)'\]\s*=\s*'(.*?)';", istek.text)
        secici     = HTMLHelper(istek.text)
        part_names = [el.text(strip=True) for el in secici.select("li.psec a")]

        async def _process_pdata(value, part_name):
            iframe_url = self._iframe_coz(value)
            if not iframe_url:
                return None
            iframe_url = self.fix_url(iframe_url)
            try:
                iframe_resp = await self.httpx.get(iframe_url, headers={"Referer": f"{self.main_url}/"})
                iframe_url  = str(iframe_resp.url)
            except Exception:
                return None
            data = await self.extract(iframe_url, referer=f"{self.main_url}/", prefix=part_name or None)
            if data:
                return data
            if "youtube.com/embed/" in iframe_url or "youtu.be/" in iframe_url:
                return [ExtractResult(
                    name    = part_name or "Fragman",
                    url     = iframe_url,
                    referer = f"{self.main_url}/",
                )]
            return None

        pdata_tasks   = []
        fragman_tasks = []
        for idx, (key, value) in enumerate(pdata_list):
            if selected_part and str(idx) != selected_part:
                continue
            part_name   = part_names[idx] if idx < len(part_names) else ""
            target_list = fragman_tasks if "fragman" in part_name.lower() or "fragman" in key.lower() else pdata_tasks
            target_list.append(_process_pdata(value, part_name))

        for data in await self.gather_with_limit(pdata_tasks):
            self.collect_results(response, data)

        # Asıl host öldüyse en azından sayfadaki açık fragman kaynağını döndür.
        if not response:
            for data in await self.gather_with_limit(fragman_tasks):
                self.collect_results(response, data)

        return response

    @staticmethod
    def _with_query(url: str, params: dict[str, str]) -> str:
        parts = list(urlsplit(url))
        parts[3] = urlencode(params)
        return urlunsplit(parts)
