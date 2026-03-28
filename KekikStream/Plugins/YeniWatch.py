# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re

class YeniWatch(PluginBase):
    name        = "YeniWatch"
    language    = "tr"
    main_url    = "https://yeniwatch.net.tr"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Yeni diziwatch yani Yeniwatch. Yabancı dizi izle, anime izle, en popüler yabancı dizileri ve animeleri ücretsiz olarak yeniwatch.net.tr'te izleyin."

    main_page   = {
        f"{main_url}/episodes/page/1/"                                                                  : "Yeni Bölümler",
        f"{main_url}/anime-arsivi/page/1/"                                                              : "Tüm Animeler",
        f"{main_url}/anime-arsivi/page/1/?filtrele=imdb&sirala=DESC&yil=&imdb=&kelime=&tur=Aksiyon"     : "Aksiyon",
        f"{main_url}/anime-arsivi/page/1/?filtrele=imdb&sirala=DESC&yil=&imdb=&kelime=&tur=İsekai"      : "İsekai",
        f"{main_url}/anime-arsivi/page/1/?filtrele=imdb&sirala=DESC&yil=&imdb=&kelime=&tur=Ecchi"       : "Ecchi",
        f"{main_url}/anime-arsivi/page/1/?filtrele=imdb&sirala=DESC&yil=&imdb=&kelime=&tur=Harem"       : "Harem",
        f"{main_url}/anime-arsivi/page/1/?filtrele=imdb&sirala=DESC&yil=&imdb=&kelime=&tur=Bilim+Kurgu" : "Bilim Kurgu",
        f"{main_url}/anime-arsivi/page/1/?filtrele=imdb&sirala=DESC&yil=&imdb=&kelime=&tur=Okul"        : "Okul",
        f"{main_url}/anime-arsivi/page/1/?filtrele=imdb&sirala=DESC&yil=&imdb=&kelime=&tur=Dram"        : "Dram",
        f"{main_url}/anime-arsivi/page/1/?filtrele=imdb&sirala=DESC&yil=&imdb=&kelime=&tur=Fantastik"   : "Fantastik",
        f"{main_url}/anime-arsivi/page/1/?filtrele=imdb&sirala=DESC&yil=&imdb=&kelime=&tur=Oyun"        : "Oyun",
        f"{main_url}/anime-arsivi/page/1/?filtrele=imdb&sirala=DESC&yil=&imdb=&kelime=&tur=Gerilim"     : "Gerilim",
        f"{main_url}/anime-arsivi/page/1/?filtrele=imdb&sirala=DESC&yil=&imdb=&kelime=&tur=Gizem"       : "Gizem",
        f"{main_url}/anime-arsivi/page/1/?filtrele=imdb&sirala=DESC&yil=&imdb=&kelime=&tur=Komedi"      : "Komedi",
        f"{main_url}/anime-arsivi/page/1/?filtrele=imdb&sirala=DESC&yil=&imdb=&kelime=&tur=Seinen"      : "Seinen",
        f"{main_url}/anime-arsivi/page/1/?filtrele=imdb&sirala=DESC&yil=&imdb=&kelime=&tur=Macera"      : "Macera",
        f"{main_url}/anime-arsivi/page/1/?filtrele=imdb&sirala=DESC&yil=&imdb=&kelime=&tur=Polisiye"    : "Polisiye",
        f"{main_url}/anime-arsivi/page/1/?filtrele=imdb&sirala=DESC&yil=&imdb=&kelime=&tur=Romantizm"   : "Romantizm",
        f"{main_url}/anime-arsivi/page/1/?filtrele=imdb&sirala=DESC&yil=&imdb=&kelime=&tur=Shounen"     : "Shounen",
        f"{main_url}/anime-arsivi/page/1/?filtrele=imdb&sirala=DESC&yil=&imdb=&kelime=&tur=Spor"        : "Spor",
        f"{main_url}/anime-arsivi/page/1/?filtrele=imdb&sirala=DESC&yil=&imdb=&kelime=&tur=Tarihi"      : "Tarihi",
    }

    def _episode_to_category_url(self, url: str) -> str:
        """Bölüm URL'sini anime kategori sayfası URL'sine çevirir"""
        match = re.match(r"^(https://yeniwatch\.net\.tr/)(.+?)(-\d+-sezon-\d+-bolum)/?$", url)
        if match:
            return f"{match.group(1)}category/{match.group(2)}/"
        return url

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        page_url = url.replace("/page/1/", f"/page/{page}/")
        istek    = await self.httpx.get(page_url)
        secici   = HTMLHelper(istek.text)

        results = []

        if "/episodes/" in url:
            for veri in secici.select("div.episode-box"):
                poster_a = veri.select_first("div.poster a")
                if not poster_a:
                    continue

                href   = poster_a.select_attr(None, "href")
                img    = poster_a.select_first("img")
                poster = img.select_attr(None, "data-src") or img.select_attr(None, "src") if img else None

                series_name = veri.select_text("div.serie-name a")
                ep_info     = veri.select_text("div.episode-name a")
                title       = f"{series_name} - {ep_info}" if series_name and ep_info else (series_name or "")

                if title and href:
                    results.append(MainPageResult(
                        category = category,
                        title    = title,
                        url      = self._episode_to_category_url(self.fix_url(href)),
                        poster   = self.fix_url(poster),
                    ))
        else:
            for veri in secici.select("div.single-item"):
                href   = veri.select_attr("div.cat-img a", "href")
                poster = veri.select_attr("div.cat-img a img", "src")
                title  = veri.select_text("div.categorytitle a")

                if title and href:
                    results.append(MainPageResult(
                        category = category,
                        title    = title,
                        url      = self._episode_to_category_url(self.fix_url(href)),
                        poster   = self.fix_url(poster),
                    ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.single-item"):
            href   = veri.select_attr("div.cat-img a", "href")
            poster = veri.select_attr("div.cat-img a img", "src")
            title  = veri.select_text("div.categorytitle a")

            if title and href:
                results.append(SearchResult(
                    title  = title.strip(),
                    url    = self._episode_to_category_url(self.fix_url(href)),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title = secici.select_text("h1") or ""
        title = re.sub(r"\s*-\s*YeniWatch$", "", title).strip()

        poster      = secici.select_attr("div.category_image img", "src")
        description = secici.select_text("div.category_desc")
        tags        = [
            t.strip() for t in secici.select_texts("div.genres a")
            if t.strip().lower() != "yeniwatch"
        ]
        year        = secici.regex_first(r"Yılı\s*:\s*</span>\s*([0-9]{4})", istek.text)
        actors_text = secici.regex_first(r"Oyuncular\s*:\s*</span>\s*([^<]+)", istek.text)
        actors      = [actor.strip() for actor in (actors_text or "").split(",") if actor.strip()]

        episodes = []
        for el in secici.select("div.bolumust"):
            ep_href  = el.select_attr("a", "href")
            ep_title = el.select_text("div.baslik")
            ep_name  = el.select_text("div.bolum-ismi")
            if ep_name:
                ep_name = re.sub(r"^\((.+)\)$", r"\1", ep_name.strip())

            if not ep_href or not ep_title:
                continue

            szn, blm = secici.extract_season_episode(ep_title)
            if szn and blm and szn > 0:
                    episodes.append(Episode(
                        season  = szn,
                        episode = blm,
                        title   = ep_name or f"Bölüm {blm}",
                        url     = self.fix_url(ep_href),
                    ))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            year        = year,
            actors      = actors,
            episodes    = episodes,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        iframe_src = secici.select_attr("iframe[src]", "src")
        if not iframe_src or "cizgipass" not in iframe_src:
            return []

        iframe_src = self.fix_url(re.sub(r"\s+", "", iframe_src))

        response = []
        data     = await self.extract(iframe_src, referer=url)
        self.collect_results(response, data)

        return self.deduplicate(response)
