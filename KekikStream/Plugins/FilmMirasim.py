# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper
import re
import json


class FilmMirasim(PluginBase):
    name        = "Film Mirasım"
    language    = "tr"
    main_url    = "https://filmmirasim.ktb.gov.tr"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Kültür ve Turizm Bakanlığı Sinema Genel Müdürlüğü arşivindeki filmlerin dijitalleştirildiği platform. Tarihi görüntüler ve yerli film arşivi."

    main_page = {
        f"{main_url}/tr/categories/6/"  : "1895-1918",
        f"{main_url}/tr/categories/5/"  : "1918-1938",
        f"{main_url}/tr/categories/18/" : "1938-1950",
        f"{main_url}/tr/categories/19/" : "1950-1960",
        f"{main_url}/tr/categories/20/" : "1960 Sonrası",
        f"{main_url}/tr/categories/23/" : "Diğer",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        full_url = url if page == 1 else f"{url.rstrip('/')}/{page}"
        istek    = await self.httpx.get(full_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for item in secici.select("div.edd_download"):
            link   = item.select_first("a")
            title  = link.attrs.get("title") or link.text(strip=True) if link else None
            href   = link.attrs.get("href") if link else None
            poster = item.select_attr("img", "src")

            if title and href:
                results.append(MainPageResult(category=category, title=title.strip(), url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        full_url = f"{self.main_url}/tr/search/0/0/{query}"
        istek    = await self.httpx.get(full_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for item in secici.select("article.entry-item"):
            link   = item.select_first("h3.entry-title a")
            title  = link.text(strip=True) if link else None
            href   = link.attrs.get("href") if link else None
            poster = item.select_attr("div.entry-thumb img", "src")

            if title and href:
                results.append(SearchResult(title=title.strip(), url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_attr("meta[property='og:title']", "content")
        poster      = self.fix_url(secici.regex_first(r'var videoThumbnail = "([^"]+)";', target=istek.text) or secici.select_attr("meta[property='og:image']", "content"))
        description = secici.select_attr("meta[property='og:description']", "content")

        # Meta verileri
        year = secici.select_text("span#ctl00_ContentPlaceHolder1_lblCekimTarihi")
        if not year or year == "-":
            year = secici.extract_year()

        tags = secici.meta_list("Kategori", container_selector=".theater_links")
        if not tags:
            keywords = secici.select_attr("meta[name='keywords']", "content")
            tags     = [t.strip() for t in keywords.split(",")] if keywords else []

        # Oyuncu/Yönetmen meta alanı (filmmirasim'de genellikle 'Oyuncular' veya 'Yönetmen' labels olur)
        actors = secici.meta_list("Oyuncular") or secici.meta_list("Yönetmen")

        # Süre
        duration_text = secici.select_text("span#ctl00_ContentPlaceHolder1_lblVideoSuresi")
        duration      = None
        if duration_text and "Süre :" in duration_text:
            time_part = duration_text.split("Süre :")[-1].strip()
            if ":" in time_part:
                parts = time_part.split(":")
                try:
                    if len(parts) == 3:
                        duration = int(parts[0]) * 60 + int(parts[1])
                    else:
                        duration = int(parts[0])
                except:
                    pass

        return MovieInfo(
            url         = url,
            poster      = poster,
            title       = title.strip() if title else "Bilinmeyen",
            description = description,
            tags        = tags,
            year        = str(year) if year and year != "-" else None,
            actors      = actors,
            duration    = duration,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek = await self.httpx.get(url)
        text  = istek.text

        # Sayfa içindeki JSON.parse('...') içindeki linkleri daha esnek yakala
        # Bazen ' bazen " kullanılır, escape karakterler olabilir
        sources_match = re.search(r"JSON\.parse\(['\"](.*?)['\"]\)", text)
        if not sources_match:
            # Direkt src: "..." formatını dene
            direct_src = re.search(r'src:\s*["\']([^"\']+\.mp4[^"\']*)["\']', text)
            if direct_src:
                return [ExtractResult(name=self.name, url=self.fix_url(direct_src.group(1)), referer=url)]
            return []

        try:
            raw_json = sources_match.group(1).encode().decode("unicode_escape")
            # Tek tırnakları çift tırnağa çevirmeyi dene (eğer JSON standardına uymuyorsa)
            if '"' not in raw_json and "'" in raw_json:
                raw_json = raw_json.replace("'", '"')

            sources_list = json.loads(raw_json)

            response = []
            for source in sources_list:
                video_url = source.get("src")
                label     = source.get("label", "Bilinmeyen")

                if video_url:
                    response.append(ExtractResult(name=f"{self.name} | {label}", url=self.fix_url(video_url), referer=url))

            return response
        except:
            # Fallback regex
            video_matches = re.findall(r'["\']src["\']\s*:\s*["\']([^"\']+)["\']', text)
            response      = []
            for v_url in video_matches:
                if ".mp4" in v_url or ".m3u8" in v_url:
                    response.append(ExtractResult(name=self.name, url=self.fix_url(v_url), referer=url))
            return response
