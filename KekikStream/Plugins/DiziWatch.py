# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
from urllib.parse     import unquote
import re

class DiziWatch(PluginBase):
    name        = "DiziWatch"
    language    = "tr"
    main_url    = "https://diziwatch.to"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Yabancı dizi izle, anime izle, en popüler yabancı dizileri ve animeleri ücretsiz olarak diziwatch.tv'de izleyin."

    main_page   = {
        f"{main_url}/episodes"                                       : "Yeni Bölümler",
        f"{main_url}/anime-arsivi?category=9&sort=date_desc"         : "Aksiyon",
        f"{main_url}/anime-arsivi?category=17&sort=date_desc"        : "Animasyon",
        f"{main_url}/anime-arsivi?category=5&sort=date_desc"         : "Bilim Kurgu",
        f"{main_url}/anime-arsivi?category=2&sort=date_desc"         : "Dram",
        f"{main_url}/anime-arsivi?category=12&sort=date_desc"        : "Fantastik",
        f"{main_url}/anime-arsivi?category=3&sort=date_desc"         : "Gizem",
        f"{main_url}/anime-arsivi?category=4&sort=date_desc"         : "Komedi",
        f"{main_url}/anime-arsivi?category=8&sort=date_desc"         : "Korku",
        f"{main_url}/anime-arsivi?category=24&sort=date_desc"        : "Macera",
        f"{main_url}/anime-arsivi?category=7&sort=date_desc"         : "Romantik",
    }

    _session_cookies = None
    _c_key           = None
    _c_value         = None

    async def _init_session(self):
        if self._session_cookies and self._c_key and self._c_value:
            return
        resp                  = await self.httpx.get(f"{self.main_url}/anime-arsivi")
        self._session_cookies = {k: unquote(v) for k, v in resp.cookies.items()}

        secici = HTMLHelper(resp.text)
        form   = secici.select_first("form")
        if form:
            inputs = form.select("input") if hasattr(form, "select") else []
            if len(inputs) >= 2:
                self._c_key   = inputs[0].select_attr(None, "value")
                self._c_value = inputs[1].select_attr(None, "value")

    def _fix_poster(self, url: str | None) -> str | None:
        if not url:
            return None
        url = url.replace("images-macellan-online.cdn.ampproject.org/i/s/", "")
        url = url.replace("file.dizilla.club", "file.macellan.online")
        url = url.replace("images.dizilla.club", "images.macellan.online")
        url = url.replace("images.dizimia4.com", "images.macellan.online")
        url = url.replace("file.dizimia4.com", "file.macellan.online")
        url = url.replace("/f/f/", "/630/910/")
        url = re.sub(r"(file\.)[^\s/]+/?", r"\1macellan.online/", url)
        url = re.sub(r"(images\.)[^\s/]+/?", r"\1macellan.online/", url)
        return self.fix_url(url)

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        await self._init_session()

        sep      = "&" if "?" in url else "?"
        page_url = f"{url}{sep}page={page}"
        istek    = await self.httpx.get(page_url, cookies=self._session_cookies, headers={"Referer": f"{self.main_url}/"})
        secici   = HTMLHelper(istek.text)

        results = []

        if "/episodes" in url:
            for veri in secici.select("div.swiper-slide a"):
                title  = veri.select_text("h2") or ""
                href   = veri.select_attr(None, "href")
                poster = veri.select_attr("img", "data-src") or veri.select_attr("img", "src")

                se_text = veri.select_text("div.flex.gap-1.items-center")
                if se_text:
                    title = f"{title} - {se_text}"

                if href:
                    href = re.sub(r"/sezon-\d+/bolum-\d+/?$", "", href)

                if title and href:
                    results.append(MainPageResult(
                        category = category,
                        title    = title.strip(),
                        url      = self.fix_url(href),
                        poster   = self._fix_poster(poster),
                    ))
        else:
            for veri in secici.select("div.content-inner a"):
                title  = veri.select_text("h2") or ""
                href   = veri.select_attr(None, "href")
                poster = veri.select_attr("img", "src") or veri.select_attr("img", "data-src")

                if title and href:
                    results.append(MainPageResult(
                        category = category,
                        title    = title.strip(),
                        url      = self.fix_url(href),
                        poster   = self._fix_poster(poster),
                    ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        await self._init_session()

        resp = await self.httpx.post(
            f"{self.main_url}/bg/searchcontent",
            cookies = self._session_cookies,
            data    = {
                "cKey"       : self._c_key  or "",
                "cValue"     : self._c_value or "",
                "searchterm" : query,
            },
            headers = {
                "X-Requested-With" : "XMLHttpRequest",
                "Accept"           : "application/json, text/javascript, */*; q=0.01",
                "Referer"          : f"{self.main_url}/",
            },
        )

        results = []
        try:
            data    = resp.json()
            items   = data.get("data", {}).get("result", [])
        except Exception:
            return results

        for item in items:
            title  = (item.get("object_name") or "").replace("\\", "")
            href   = (item.get("used_slug") or "").replace("\\", "")
            poster = self._fix_poster(item.get("object_poster_url"))

            if title and href:
                results.append(SearchResult(
                    title  = title.strip(),
                    url    = self.fix_url(href),
                    poster = poster,
                ))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("h2") or ""
        poster      = secici.select_attr("img.rounded-md", "src")
        description = secici.select_text("div.text-sm.text-white p")
        tags_el     = secici.select_text("div.text-sm:nth-child(3) span.text-white:nth-child(3)")
        tags        = [t.strip() for t in tags_el.split(",")] if tags_el else []

        year = secici.extract_year("div.text-sm:nth-child(2) span.text-white:nth-child(3)")

        episodes = []
        for bolum in secici.select("ul a"):
            b_href = bolum.select_attr(None, "href")
            if not b_href:
                continue

            b_name  = bolum.select_text("span.hidden.sm\\:block") or bolum.select_text("span.hidden")
            se_text = bolum.select_text("span.text-sm") or ""

            b_season = None
            b_ep     = None
            if "." in se_text:
                parts = se_text.split(".")
                try:
                    b_season = int(parts[0])
                except ValueError:
                    pass
                remain = parts[-1].strip().split(" ")[0] if len(parts) > 1 else ""
                try:
                    b_ep = int(remain)
                except ValueError:
                    pass

            episodes.append(Episode(
                season  = b_season or 1,
                episode = b_ep,
                title   = b_name or f"Bölüm {b_ep}" if b_ep else "Bölüm",
                url     = self.fix_url(b_href),
            ))

        return SeriesInfo(
            url         = url,
            poster      = self._fix_poster(poster),
            title       = title,
            description = description,
            tags        = tags,
            year        = year,
            episodes    = episodes,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        iframe = secici.select_attr("iframe", "src")
        if not iframe:
            return []

        iframe   = self.fix_url(iframe)
        response = []
        data     = await self.extract(iframe, referer=f"{self.main_url}/")
        self.collect_results(response, data)

        return response
