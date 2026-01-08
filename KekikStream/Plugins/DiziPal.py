# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, Subtitle, ExtractResult, HTMLHelper

class DiziPal(PluginBase):
    name        = "DiziPal"
    language    = "tr"
    main_url    = "https://dizipal1225.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "dizipal güncel, dizipal yeni ve gerçek adresi. dizipal en yeni dizi ve filmleri güvenli ve hızlı şekilde sunar."

    main_page   = {
        f"{main_url}/diziler/son-bolumler"              : "Son Bölümler",
        f"{main_url}/diziler"                           : "Yeni Diziler",
        f"{main_url}/filmler"                           : "Yeni Filmler",
        f"{main_url}/koleksiyon/netflix"                : "Netflix",
        f"{main_url}/koleksiyon/exxen"                  : "Exxen",
        f"{main_url}/koleksiyon/blutv"                  : "BluTV",
        f"{main_url}/koleksiyon/disney"                 : "Disney+",
        f"{main_url}/koleksiyon/amazon-prime"           : "Amazon Prime",
        f"{main_url}/koleksiyon/tod-bein"               : "TOD (beIN)",
        f"{main_url}/koleksiyon/gain"                   : "Gain",
        f"{main_url}/tur/mubi"                          : "Mubi",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        results = []

        if "/son-bolumler" in url:
            for veri in secici.select("div.episode-item"):
                name    = secici.select_text("div.name", veri)
                episode = secici.select_text("div.episode", veri)
                href    = secici.select_attr("a", "href", veri)
                poster  = secici.select_attr("img", "src", veri)

                if name and href:
                    ep_text = episode.replace(". Sezon ", "x").replace(". Bölüm", "") if episode else ""
                    title   = f"{name} {ep_text}"
                    # Son bölümler linkini dizi sayfasına çevir
                    dizi_url = href.split("/sezon")[0] if "/sezon" in href else href

                    results.append(MainPageResult(
                        category = category,
                        title    = title,
                        url      = self.fix_url(dizi_url),
                        poster   = self.fix_url(poster) if poster else None,
                    ))
        else:
            for veri in secici.select("article.type2 ul li"):
                title  = secici.select_text("span.title", veri)
                href   = secici.select_attr("a", "href", veri)
                poster = secici.select_attr("img", "src", veri)

                if title and href:
                    results.append(MainPageResult(
                        category = category,
                        title    = title,
                        url      = self.fix_url(href),
                        poster   = self.fix_url(poster) if poster else None,
                    ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        self.httpx.headers.update({
            "Accept"           : "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With" : "XMLHttpRequest"
        })

        istek = await self.httpx.post(
            url  = f"{self.main_url}/api/search-autocomplete",
            data = {"query": query}
        )

        try:
            data = istek.json()
        except Exception:
            return []

        results = []

        # API bazen dict, bazen list döner
        items = data.values() if isinstance(data, dict) else data

        for item in items:
            if not isinstance(item, dict):
                continue

            title  = item.get("title")
            url    = item.get("url")
            poster = item.get("poster")

            if title and url:
                results.append(SearchResult(
                    title  = title,
                    url    = f"{self.main_url}{url}",
                    poster = self.fix_url(poster) if poster else None,
                ))

        return results

    def _find_sibling_text(self, secici: HTMLHelper, label_text: str) -> str | None:
        """Bir label'ın kardeş div'inden text çıkarır (xpath yerine)"""
        for div in secici.select("div"):
            if secici.select_text(element=div) == label_text:
                # Sonraki kardeş elementi bul
                next_sibling = div.next
                while next_sibling:
                    if hasattr(next_sibling, 'text') and next_sibling.text(strip=True):
                        return next_sibling.text(strip=True)
                    next_sibling = next_sibling.next if hasattr(next_sibling, 'next') else None
        return None

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        # Reset headers to get HTML response
        self.httpx.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })
        self.httpx.headers.pop("X-Requested-With", None)

        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)
        html_text = istek.text

        poster   = self.fix_url(secici.select_attr("meta[property='og:image']", "content")) if secici.select_attr("meta[property='og:image']", "content") else None

        # XPath yerine regex ile HTML'den çıkarma
        year = secici.regex_first(r'(?is)Yapım Yılı.*?<div[^>]*>(\d{4})</div>', secici.html)

        description = secici.select_text("div.summary p")

        rating = secici.regex_first(r'(?is)IMDB Puanı.*?<div[^>]*>([0-9.]+)</div>', secici.html)

        tags_raw = secici.regex_first(r'(?is)Türler.*?<div[^>]*>([^<]+)</div>', secici.html)
        tags = [t.strip() for t in tags_raw.split() if t.strip()] if tags_raw else None

        duration_raw = secici.regex_first(r'(?is)Ortalama Süre.*?<div[^>]*>(\d+)', secici.html)
        duration = int(duration_raw) if duration_raw else None

        if "/dizi/" in url:
            title    = secici.select_text("div.cover h5")

            episodes = []
            for ep in secici.select("div.episode-item"):
                ep_name = secici.select_text("div.name", ep)
                ep_href = secici.select_attr("a", "href", ep)
                ep_text = secici.select_text("div.episode", ep)
                ep_parts = ep_text.split(" ")

                ep_season  = None
                ep_episode = None
                if len(ep_parts) >= 4:
                    try:
                        ep_season  = int(ep_parts[0].replace(".", ""))
                        ep_episode = int(ep_parts[2].replace(".", ""))
                    except ValueError:
                        pass

                if ep_name and ep_href:
                    episodes.append(Episode(
                        season  = ep_season,
                        episode = ep_episode,
                        title   = ep_name,
                        url     = self.fix_url(ep_href),
                    ))

            return SeriesInfo(
                url         = url,
                poster      = poster,
                title       = title,
                description = description,
                tags        = tags,
                rating      = rating,
                year        = year,
                duration    = duration,
                episodes    = episodes if episodes else None,
            )
        else:
            # Film için title - g-title div'lerinin 2. olanı
            g_titles = secici.select("div.g-title div")
            title = secici.select_text(element=g_titles[1]) if len(g_titles) >= 2 else None

            return MovieInfo(
                url         = url,
                poster      = poster,
                title       = title,
                description = description,
                tags        = tags,
                rating      = rating,
                year        = year,
                duration    = duration,
            )

    async def load_links(self, url: str) -> list[ExtractResult]:
        # Reset headers to get HTML response
        self.httpx.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        })
        self.httpx.headers.pop("X-Requested-With", None)

        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

            # iframe presence checked via select_attr below

        iframe = secici.select_attr(".series-player-container iframe", "src") or secici.select_attr("div#vast_new iframe", "src")
        if not iframe:
            return []

        results = []

        self.httpx.headers.update({"Referer": f"{self.main_url}/"})
        i_istek = await self.httpx.get(iframe)
        i_text  = i_istek.text

        # m3u link çıkar
        m3u_link = secici.regex_first(r'file:"([^"]+)"', target=i_text)
        if m3u_link:

            # Altyazıları çıkar
            sub_text = secici.regex_first(r'"subtitle":"([^"]+)"', target=i_text)
            subtitles = []
            if sub_text:
                if "," in sub_text:
                    for sub in sub_text.split(","):
                        lang = sub.split("[")[1].split("]")[0] if "[" in sub else "Türkçe"
                        sub_url = sub.replace(f"[{lang}]", "")
                        subtitles.append(Subtitle(name=lang, url=self.fix_url(sub_url)))
                else:
                    lang = sub_text.split("[")[1].split("]")[0] if "[" in sub_text else "Türkçe"
                    sub_url = sub_text.replace(f"[{lang}]", "")
                    subtitles.append(Subtitle(name=lang, url=self.fix_url(sub_url)))

            results.append(ExtractResult(
                name      = self.name,
                url       = m3u_link,
                referer   = f"{self.main_url}/",
                subtitles = subtitles
            ))
        else:
            # Extractor'a yönlendir
            data = await self.extract(iframe)
            if data:
                results.append(data)

        return results
