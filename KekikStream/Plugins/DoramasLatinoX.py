# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
import re

class DoramasLatinoX(PluginBase):
    name        = "DoramasLatinoX"
    language    = "mx"
    main_url    = "https://doramaslatinox.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Doramas en Audio Español Latino y Subtitulado"

    main_page = {
        f"{main_url}/movies/"             : "Todas las Películas",
        f"{main_url}/estado/completo/"    : "Completos",
        f"{main_url}/estado/emision/"     : "En Emision",
        f"{main_url}/audio/latino/"       : "Latino",
        f"{main_url}/audio/subtitulado/"  : "Subtitulado",
        f"{main_url}/tipo/dorama/"        : "Doramas",
        f"{main_url}/tipo/serie/"         : "Series",
        f"{main_url}/pais/corea-del-sur/" : "Corea del Sur",
        f"{main_url}/pais/china/"         : "China",
        f"{main_url}/pais/japon/"         : "Japón",
        f"{main_url}/pais/tailandia/"     : "Tailandia",
        f"{main_url}/series/"             : "Todas las Series",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        full_url = url if page <= 1 else f"{url.rstrip('/')}/page/{page}/"
        istek    = await self.httpx.get(full_url)
        secici   = HTMLHelper(istek.text)

        results = []
        for item in secici.select("article.item"):
            link   = item.select_first("div.data h3 a")
            title  = link.text(strip=True) if link else None
            href   = link.attrs.get("href") if link else None
            poster = item.select_poster("div.poster img")

            if title and href:
                results.append(MainPageResult(category=category, title=title.strip(), url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        # Search URL: Query param 's' kullanılmalı (Follow redirects for search/ query)
        full_url = f"{self.main_url}/?s={query}"
        try:
            istek = await self.httpx.get(full_url, follow_redirects=True, timeout=15)
            html  = istek.text
        except Exception:
            istek = await self.async_cf_get(full_url, headers=self._headers)
            html  = istek.text

        secici = HTMLHelper(html)

        results = []
        # Arama sonuçları listesi bazen farklı selector kullanabiliyor
        items = secici.select("div.result-item article") or secici.select("article.item")
        for item in items:
            link   = item.select_first("div.details div.title a") or item.select_first("div.data h3 a")
            title  = link.text(strip=True) if link else None
            href   = link.attrs.get("href") if link else None
            poster = item.select_poster("div.image img") or item.select_poster("div.poster img")

            if title and href:
                results.append(SearchResult(title=title.strip(), url=self.fix_url(href), poster=self.fix_url(poster)))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("h1")
        poster      = secici.select_attr("meta[property='og:image']", "content")
        description = secici.select_attr("meta[property='og:description']", "content") or secici.select_text(".wp-content p") or secici.select_text("#info p")

        # Meta verileri
        year   = secici.extract_year("div.extra span")
        tags   = secici.select_texts("div.sgeneros a")
        rating = secici.select_text("span.dt_rating_vgs")
        actors = [person.select_text("div.name a") for person in secici.select("div.person") if person.select_text("div.name a")]

        episodes = []
        for ep in secici.select("ul.episodios a"):
            href     = ep.attrs.get("href")
            num_text = ep.select_text("div.numerando") or "1-1"

            try:
                parts   = num_text.split("-")
                season  = int(parts[0]) if len(parts) > 0 else 1
                episode = int(parts[-1]) if len(parts) > 1 else 1
            except:
                season, episode = 1, 1

            ep_title  = ep.select_text("div.episodiotitle")
            ep_poster = ep.select_poster("img")

            if href:
                episodes.append(
                    Episode(
                        season  = season,
                        episode = episode,
                        title   = ep_title or f"Episodio {episode}",
                        url     = self.fix_url(href),
                        poster  = self.fix_url(ep_poster),
                    )
                )

        if episodes:
            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = title.strip() if title else "Bilinmeyen",
                description = description,
                tags        = tags,
                year        = str(year) if year else None,
                rating      = rating,
                actors      = actors,
                episodes    = episodes,
            )

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title.strip() if title else "Bilinmeyen",
            description = description,
            tags        = tags,
            year        = str(year) if year else None,
            rating      = rating,
            actors      = actors,
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        try:
            istek = await self.httpx.get(url, timeout=15)
            html  = istek.text
        except Exception:
            istek = await self.async_cf_get(url, headers=self._headers)
            html  = istek.text

        secici = HTMLHelper(html)

        response = []
        tasks    = []

        async def fetch_dooplayer(post, p_type, nume):
            api_url = f"{self.main_url}/wp-json/dooplayer/v2/{post}/{p_type}/{nume}"
            try:
                r         = await self.httpx.get(api_url)
                data      = r.json()
                embed_url = data.get("embed_url")
                if embed_url:
                    # HTML içerebilir, regex ile linki ayıkla (whitespace ve tek slash toleranslı)
                    link_match = re.search(r'src=\s*["\']?\s*(https?:/{1,2}[^"\'>\s]+)', embed_url)
                    if link_match:
                        raw    = link_match.group(1).strip()
                        target = re.sub(r'^(https?:)/([^/])', r'\1//\2', raw)
                        target = self.fix_url(target)
                    elif embed_url.startswith("http"):
                        target = self.fix_url(embed_url)
                    else:
                        return None

                    if not any(x in target.lower() for x in ["google", "facebook", "ads", "analytics", "democraticexit"]):
                        return await self.extract(target, referer=url)
            except:
                pass
            return None

        # Player seçeneklerini tara
        for opt in secici.select("li.dooplay_player_option"):
            post   = opt.attrs.get("data-post")
            p_type = opt.attrs.get("data-type")
            nume   = opt.attrs.get("data-nume")

            if post and p_type and nume:
                tasks.append(fetch_dooplayer(post, p_type, nume))

        # Sayfadaki tüm iframe'leri tara
        for iframe in secici.select("iframe"):
            src = self.fix_url(iframe.attrs.get("data-src") or iframe.attrs.get("src") or "")
            if src and not any(x in src.lower() for x in ["google", "facebook", "ads", "analytics", "data:image"]):
                tasks.append(self.extract(src, referer=url))

        results = await self.gather_with_limit(tasks)
        for res in results:
            self.collect_results(response, res)

        return response
