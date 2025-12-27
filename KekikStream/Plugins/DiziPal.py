# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, Subtitle, ExtractResult
from selectolax.parser import HTMLParser
import re

class DiziPal(PluginBase):
    name        = "DiziPal"
    language    = "tr"
    main_url    = "https://dizipal1224.com"
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
        secici = HTMLParser(istek.text)

        results = []

        if "/son-bolumler" in url:
            for veri in secici.css("div.episode-item"):
                name_el    = veri.css_first("div.name")
                episode_el = veri.css_first("div.episode")
                link_el    = veri.css_first("a")
                img_el     = veri.css_first("img")

                name    = name_el.text(strip=True) if name_el else None
                episode = episode_el.text(strip=True) if episode_el else None
                href    = link_el.attrs.get("href") if link_el else None
                poster  = img_el.attrs.get("src") if img_el else None

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
            for veri in secici.css("article.type2 ul li"):
                title_el = veri.css_first("span.title")
                link_el  = veri.css_first("a")
                img_el   = veri.css_first("img")

                title  = title_el.text(strip=True) if title_el else None
                href   = link_el.attrs.get("href") if link_el else None
                poster = img_el.attrs.get("src") if img_el else None

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

    def _find_sibling_text(self, secici: HTMLParser, label_text: str) -> str | None:
        """Bir label'ın kardeş div'inden text çıkarır (xpath yerine)"""
        for div in secici.css("div"):
            if div.text(strip=True) == label_text:
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
        secici = HTMLParser(istek.text)
        html_text = istek.text

        og_image = secici.css_first("meta[property='og:image']")
        poster   = self.fix_url(og_image.attrs.get("content")) if og_image else None

        # XPath yerine regex ile HTML'den çıkarma
        year = None
        year_match = re.search(r'Yapım Yılı.*?<div[^>]*>(\d{4})</div>', html_text, re.DOTALL | re.IGNORECASE)
        if year_match:
            year = year_match.group(1)

        desc_el     = secici.css_first("div.summary p")
        description = desc_el.text(strip=True) if desc_el else None

        rating = None
        rating_match = re.search(r'IMDB Puanı.*?<div[^>]*>([0-9.]+)</div>', html_text, re.DOTALL | re.IGNORECASE)
        if rating_match:
            rating = rating_match.group(1)

        tags = None
        tags_match = re.search(r'Türler.*?<div[^>]*>([^<]+)</div>', html_text, re.DOTALL | re.IGNORECASE)
        if tags_match:
            tags_raw = tags_match.group(1)
            tags = [t.strip() for t in tags_raw.split() if t.strip()]

        duration = None
        dur_match = re.search(r'Ortalama Süre.*?<div[^>]*>(\d+)', html_text, re.DOTALL | re.IGNORECASE)
        if dur_match:
            duration = int(dur_match.group(1))

        if "/dizi/" in url:
            title_el = secici.css_first("div.cover h5")
            title    = title_el.text(strip=True) if title_el else None

            episodes = []
            for ep in secici.css("div.episode-item"):
                ep_name_el    = ep.css_first("div.name")
                ep_link_el    = ep.css_first("a")
                ep_episode_el = ep.css_first("div.episode")

                ep_name = ep_name_el.text(strip=True) if ep_name_el else None
                ep_href = ep_link_el.attrs.get("href") if ep_link_el else None
                ep_text = ep_episode_el.text(strip=True) if ep_episode_el else ""
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
            g_titles = secici.css("div.g-title div")
            title = g_titles[1].text(strip=True) if len(g_titles) >= 2 else None

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
        secici = HTMLParser(istek.text)

        iframe_el = secici.css_first(".series-player-container iframe")
        if not iframe_el:
            iframe_el = secici.css_first("div#vast_new iframe")

        iframe = iframe_el.attrs.get("src") if iframe_el else None
        if not iframe:
            return []

        results = []

        self.httpx.headers.update({"Referer": f"{self.main_url}/"})
        i_istek = await self.httpx.get(iframe)
        i_text  = i_istek.text

        # m3u link çıkar
        m3u_match = re.search(r'file:"([^"]+)"', i_text)
        if m3u_match:
            m3u_link = m3u_match[1]

            # Altyazıları çıkar
            subtitles = []
            sub_match = re.search(r'"subtitle":"([^"]+)"', i_text)
            if sub_match:
                sub_text = sub_match[1]
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
