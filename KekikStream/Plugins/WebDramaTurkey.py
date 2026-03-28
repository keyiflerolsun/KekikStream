# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re

class WebDramaTurkey(PluginBase):
    name        = "WebDramaTurkey"
    language    = "tr"
    main_url    = "https://webdramaturkey2.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Kore dizisi izle, çin dizisi izle, japon dizisi izle, kore dizileri izle, kore filmleri, asya dizileri, çin filmleri, japon filmleri, bl dizi izle, asya dizisi izle, web drama izle."

    main_page   = {
        f"{main_url}/"                : "Son Bölümler",
        f"{main_url}/diziler"         : "Diziler",
        f"{main_url}/filmler"         : "Filmler",
        f"{main_url}/anime"           : "Animeler",
        f"{main_url}/tur/romantik"    : "Romantik",
        f"{main_url}/tur/fantastik"   : "Fantastik",
        f"{main_url}/tur/dram"        : "Dram",
        f"{main_url}/tur/korku"       : "Korku",
        f"{main_url}/tur/gerilim"     : "Gerilim",
        f"{main_url}/tur/komedi"      : "Komedi",
        f"{main_url}/tur/muzik"       : "Müzik",
        f"{main_url}/tur/gizem"       : "Gizem",
        f"{main_url}/tur/bl"          : "BL",
        f"{main_url}/tur/genclik"     : "Gençlik",
        f"{main_url}/tur/web-drama"   : "Web Drama",
        f"{main_url}/tur/aksiyon"     : "Aksiyon",
        f"{main_url}/tur/tarihi"      : "Tarihi",
        f"{main_url}/tur/bilim-kurgu" : "Bilim Kurgu",
        f"{main_url}/tur/wuxia"       : "Wuxia",
        f"{main_url}/tur/xianxia"     : "Xianxia",
        f"{main_url}/tur/aile"        : "Aile",
        f"{main_url}/tur/suc"         : "Suç",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        page_url = url if url.endswith("/") else f"{url}?page={page}"
        istek    = await self.httpx.get(page_url)
        secici   = HTMLHelper(istek.text)

        results = []

        if url.endswith("/"):
            # Son Bölümler
            for veri in secici.select("div.col.sonyuklemeler"):
                title_el = veri.select_text("div.list-title") or ""
                cat_el   = veri.select_text("div.list-category") or ""
                title    = f"{title_el} - {cat_el}" if title_el and cat_el else title_el

                href = veri.select_attr("a", "href")
                if href:
                    href = re.sub(r"/\d+-sezon/\d+-bolum$", "/", href)

                poster   = None
                media_el = veri.select_first("div.media.media-episode")
                if media_el:
                    style = media_el.get("style") if hasattr(media_el, "get") else ""
                    if style:
                        style_decoded = style.replace("&quot;", '"')
                        m             = re.search(r'url\("([^"]+)"\)', style_decoded)
                        if m:
                            poster = m.group(1)
                    if not poster:
                        poster = media_el.select_attr(None, "data-src") if media_el else None

                if title and href:
                    results.append(MainPageResult(
                        category = category,
                        title    = title,
                        url      = self.fix_url(href),
                        poster   = self.fix_url(poster),
                    ))
        else:
            for veri in secici.select("div.col"):
                title  = veri.select_text("a.list-title")
                href   = veri.select_attr("a", "href")
                poster = veri.select_attr("div.media.media-cover", "data-src")

                if title and href:
                    results.append(MainPageResult(
                        category = category,
                        title    = title,
                        url      = self.fix_url(href),
                        poster   = self.fix_url(poster),
                    ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/arama/{query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.col"):
            title  = veri.select_text("a.list-title")
            href   = veri.select_attr("a", "href")
            poster = veri.select_attr("div.media.media-cover", "data-src")

            if title and href:
                results.append(SearchResult(
                    title  = title.strip(),
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("h1") or ""
        poster      = secici.select_attr("div.media.media-cover", "data-src")
        description = secici.select_text("div.text-content") or secici.select_text("div.video-attr:nth-child(4) > div:nth-child(2)")
        tags        = secici.select_texts("div.categories a") or secici.select_texts("div.category a")

        year = secici.extract_year("div.featured-attr:nth-child(1) > div:nth-child(2)", "div.video-attr:nth-child(3) > div:nth-child(2)")

        if "/film/" in url:
            return MovieInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = title,
                description = description,
                tags        = tags,
                year        = year,
            )

        episodes = []
        for bolum in secici.select("div.episodes a"):
            b_href   = bolum.select_attr(None, "href")
            b_num    = bolum.select_text("div.episode")
            b_ep     = None
            b_season = 1

            if b_num:
                ep_match = re.search(r"(\d+)", b_num)
                if ep_match:
                    b_ep = int(ep_match.group(1))

            if b_href:
                szn_match = re.search(r"/(\d+)-sezon", b_href)
                if szn_match:
                    b_season = int(szn_match.group(1))

            if b_href:
                episodes.append(Episode(
                    season  = b_season,
                    episode = b_ep,
                    title   = f"Bölüm {b_ep}" if b_ep else "Bölüm",
                    url     = self.fix_url(b_href),
                ))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            year        = year,
            episodes    = episodes,
        )

    async def _handle_dtpasn(self, iframe_url: str, referer: str) -> list[ExtractResult]:
        """dtpasn.asia SecuredLink patternı"""
        results = []
        try:
            video_id = iframe_url.split("dtpasn.asia/video/")[1].split("?")[0] if "dtpasn.asia/video/" in iframe_url else ""
            if not video_id:
                return results

            iframe_resp = await self.httpx.get(iframe_url, headers={"Referer": referer})
            cookie      = iframe_resp.cookies.get("fireplayer_player", "")

            resp = await self.httpx.post(
                f"https://dtpasn.asia/player/index.php?data={video_id}&do=getVideo",
                headers = {
                    "X-Requested-With" : "XMLHttpRequest",
                    "Content-Type"     : "application/x-www-form-urlencoded; charset=UTF-8",
                    "Referer"          : iframe_url,
                    "Origin"           : "https://dtpasn.asia",
                },
                cookies = {"fireplayer_player": cookie} if cookie else {},
            )

            data = resp.json()
            for key in ("videoSource", "securedLink"):
                link = data.get(key, "")
                if link:
                    results.append(ExtractResult(
                        name    = f"WDT",
                        url     = link,
                        referer = "https://dtpasn.asia/",
                    ))
        except Exception:
            pass

        return results

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        response = []

        embed_ids = []
        for el in secici.select("[data-embed]"):
            eid = el.select_attr(None, "data-embed")
            if eid and eid not in embed_ids:
                embed_ids.append(eid)

        async def _process_embed(eid):
            try:
                resp = await self.httpx.post(
                    f"{self.main_url}/ajax/embed",
                    data    = {"id": eid},
                    headers = {
                        "X-Requested-With" : "XMLHttpRequest",
                        "Content-Type"     : "application/x-www-form-urlencoded; charset=UTF-8",
                        "Referer"          : url,
                    },
                )

                embed_secici = HTMLHelper(resp.text)
                iframe_src   = embed_secici.select_attr("iframe", "src")
                if not iframe_src:
                    return None

                # İkinci iframe katmanı
                if_resp   = await self.httpx.get(iframe_src, headers={"Referer": url})
                if_secici = HTMLHelper(if_resp.text)
                final_src = if_secici.select_attr("iframe", "src")
                if final_src:
                    final_src = final_src.split("#")[0]
                else:
                    final_src = iframe_src

                final_src = self.fix_url(final_src)

                if "dtpasn.asia/video/" in final_src:
                    return await self._handle_dtpasn(final_src, url)
                else:
                    return await self.extract(final_src, referer=f"{self.main_url}/")
            except Exception:
                return None

        tasks    = [_process_embed(eid) for eid in embed_ids]
        response = []
        for data in await self.gather_with_limit(tasks):
            self.collect_results(response, data)

        return self.deduplicate(response)
