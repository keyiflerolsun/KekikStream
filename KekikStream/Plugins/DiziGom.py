# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
from Kekik.Sifreleme  import Packer
import json, re

class DiziGom(PluginBase):
    name        = "DiziGom"
    language    = "tr"
    main_url    = "https://dizigom104.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Türkçe altyazılı yabancı dizi izle, Tüm yabancı, kore, netflix dizilerin yeni ve eski sezonlarını orijinal dilinde dizigom1 alt yazılı film izleyebilir, sadece türkçe altyazılı en iyi yabancı diziler ve filmler hakkında yorum yapabilirsiniz."

    main_page   = {
        f"{main_url}/tur/aile/"        : "Aile",
        f"{main_url}/tur/aksiyon/"     : "Aksiyon",
        f"{main_url}/tur/animasyon/"   : "Animasyon",
        f"{main_url}/tur/belgesel/"    : "Belgesel",
        f"{main_url}/tur/bilim-kurgu/" : "Bilim Kurgu",
        f"{main_url}/tur/dram/"        : "Dram",
        f"{main_url}/tur/fantastik/"   : "Fantastik",
        f"{main_url}/tur/gerilim/"     : "Gerilim",
        f"{main_url}/tur/komedi/"      : "Komedi",
        f"{main_url}/tur/korku/"       : "Korku",
        f"{main_url}/tur/macera/"      : "Macera",
        f"{main_url}/tur/polisiye/"    : "Polisiye",
        f"{main_url}/tur/romantik/"    : "Romantik",
        f"{main_url}/tur/savas/"       : "Savaş",
        f"{main_url}/tur/suc/"         : "Suç",
        f"{main_url}/tur/tarih/"       : "Tarih",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}#p={page}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.episode-box"):
            title  = veri.select_text("div.serie-name a")
            href   = veri.select_attr("a", "href")
            poster = veri.select_attr("img", "src")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.single-item"):
            title  = veri.select_text("div.categorytitle a")
            href   = veri.select_attr("div.categorytitle a", "href")
            poster = veri.select_attr("img", "src")

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

        # Dizi sayfası
        title       = secici.select_text("div.serieTitle h1")
        if title:
            poster_style = secici.select_attr("div.seriePoster", "style") or ""
            poster       = re.search(r"url\(([^)]+)\)", poster_style)
            poster      = poster.group(1) if poster else ""
            description = secici.select_text("div.serieDescription p")
            year        = secici.select_text("div.airDateYear a")
            tags        = secici.select_texts("div.genreList a")
            rating      = secici.select_text("div.score")

            episodes = []
            for veri in secici.select("div.bolumust"):
                ep_href   = veri.select_attr("a", "href")
                ep_name   = veri.select_text("div.bolum-ismi")
                ep_title  = veri.select_text("div.baslik") or ""

                parts   = ep_title.split()
                season  = int(parts[0].replace(".", "")) if parts else 1
                episode = int(parts[2].replace(".", "")) if len(parts) > 2 else 1

                if ep_href:
                    episodes.append(Episode(
                        season  = season,
                        episode = episode,
                        title   = ep_name or f"{season}. Sezon {episode}. Bölüm",
                        url     = self.fix_url(ep_href),
                    ))

            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = title,
                description = description,
                tags        = tags,
                year        = year,
                rating      = rating,
                episodes    = episodes,
            )

        # Film sayfası — OG meta + JSON-LD
        og_title = secici.select_attr("meta[property=\"og:title\"]", "content") or ""
        title    = og_title.split(" türkçe")[0].split(" izle")[0].strip() if og_title else ""
        poster   = secici.select_attr("meta[property=\"og:image\"]", "content") or ""
        og_desc  = secici.select_attr("meta[property=\"og:description\"]", "content") or ""
        description = og_desc.split(" türkçe")[0].split(" izle -")[0].strip() if og_desc else ""

        rating = secici.select_text("div.score") or secici.regex_first(r'"ratingValue"\s*:\s*"([^"]+)"')
        year   = secici.regex_first(r'"dateCreated"\s*:\s*"(\d{4})')

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            year        = year,
            rating      = rating,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url, headers={"Referer": f"{self.main_url}/"})
        secici = HTMLHelper(istek.text)

        # JSON-LD contentUrl çıkar
        script_data = secici.select_first("div#content script")
        if not script_data:
            return []

        try:
            json_data   = json.loads(script_data.text())
            content_url = json_data.get("contentUrl", "")
        except Exception:
            return []

        if not content_url:
            return []

        # https:// → https://play. dönüşümü
        play_url = content_url.replace("https://", "https://play.")

        iframe_resp = await self.httpx.get(play_url, headers={"Referer": f"{self.main_url}/"})

        # JsUnpacker
        packed_match = re.search(r"(eval\s*\(\s*function[\s\S]+?)<\/script>", iframe_resp.text)
        if not packed_match:
            return []

        unpacked = Packer.unpack(packed_match.group(1))

        # sources:[{...}] çıkar
        source_json = re.search(r'sources:\[\{(.*?)\}', unpacked)
        if not source_json:
            return []

        try:
            source_str = "{" + source_json.group(1).replace("\\/", "/") + "}"
            # Basit JSON parse: file, label, type
            file_match = re.search(r'"?file"?\s*:\s*"([^"]+)"', source_str)
            if file_match:
                m3u8_url = file_match.group(1)
                return [ExtractResult(
                    name    = self.name,
                    url     = m3u8_url,
                    referer = f"{self.main_url}/",
                )]
        except Exception:
            pass

        return []
