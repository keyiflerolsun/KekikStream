# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
import base64, re, json

class Coflix(PluginBase):
    name        = "Coflix"
    language    = "fr"
    main_url    = "https://coflix.rodeo"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Regarder des Films en ligne Coflix✓ Voir Série en ligne Complète Films et séries coflix en haute qualité.qualité full HD"

    _api_url    = f"{main_url}/wp-json/apiflix/v1"

    main_page   = {
        "movies"                             : "Films",
        "movies&genres=animation"            : "Animation",
        "movies&genres=aventure"             : "Aventure",
        "movies&genres=comedie"              : "Comédie",
        "movies&genres=familial"             : "Familial",
        "movies&genres=mystere"              : "Mystère",
        "movies&genres=crimen"               : "Crimen",
        "movies&genres=action-adventure"     : "Action & Adventure",
        "movies&genres=documental"           : "Documental",
        "series"                             : "Séries",
        "series&genres=drama"                : "Drama",
        "series&genres=comedia"              : "Comedia",
        "series&genres=misterio"             : "Misterio",
        "series&genres=reality"              : "Reality",
        "doramas" : "Doramas",
        "animes"  : "Animes",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        # url is our key (movies, series, etc.)
        api_target = f"{self._api_url}/options/?years=&post_type={url}&genres=&page={page}&sort=1"
        istek      = await self.httpx.get(api_target)
        try:
            data    = istek.json()
            results = []
            for item in data.get("results", []):
                title = self.clean_title(item.get("name", "Unknown"))
                href  = self.fix_url(item.get("url", ""))

                # Poster from HTML path usually contains img tag
                poster_html = item.get("path", "")
                poster      = self._extract_img_src(poster_html)

                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = href,
                    poster   = poster
                ))
            return results
        except Exception:
            return []

    def _extract_img_src(self, html: str) -> str:
        if not html:
            return ""
        match = re.search(r'src="([^"]+)"', html)
        if not match:
            return ""
        url = match.group(1)
        return f"https:{url}" if url.startswith("//") else url

    async def search(self, query: str) -> list[SearchResult]:
        # Kotlin uses suggest.php
        link  = f"{self.main_url}/suggest.php?query={query}"
        istek = await self.httpx.get(link)
        try:
            # Re-format broken JSON if any, Kotlin says .toString().toJson() which implies some cleanup
            text = istek.text
            # Sometimes suggest.php returns raw list or needs parsing
            data    = json.loads(text)
            results = []
            for item in data:
                title  = self.clean_title(item.get("title", "Unknown"))
                href   = self.fix_url(item.get("url", ""))
                poster = self._extract_img_src(item.get("image", ""))

                results.append(SearchResult(
                    title  = title,
                    url    = href,
                    poster = poster
                ))
            return results
        except Exception:
            return []

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title = secici.select_text("meta[property='og:title']")
        if title:
            title = title.split(" En ")[0].strip()
        else:
            title = secici.select_text("h1") or "Unknown"

        title = self.clean_title(title)

        poster = self.fix_url(secici.select_attr("img.TPostBg", "src") or self._extract_img_src(str(secici.select_first("div.title-img img"))))

        desc = secici.select_text("div.summary.link-co p") or secici.select_text("div.summary article p") or secici.regex_first(r'<meta name="description" content="([^"]+)"')

        tags     = [a.text().strip() for a in secici.select("div.meta.df.aic.fww a")]
        rating   = secici.regex_first(r"IMDb.*?([\d\.]+)") or "0"
        pres_el  = secici.select_first("p  #pres")
        year     = secici.regex_first(r"(\d{4})", target=pres_el.text()) if pres_el else secici.regex_first(r"(\d{4})")
        actors   = ", ".join([a.text().strip() for a in secici.select("p.cast a") or secici.select("div.dtls a[href*='/actors/']") or secici.select("div.cast a") or secici.select("div.f-info-desc a")])
        duration = secici.regex_first(r"(\d+)\s+min")

        is_series = "film" not in url
        if is_series:
            episodes = []
            # Seasons are in section.sc-seasons ul li input
            for s_input in secici.select("section.sc-seasons ul li input"):
                s_num = s_input.attrs.get("data-season")
                p_id  = s_input.attrs.get("post-id")
                if not s_num or not p_id:
                    continue

                # API Call for season episodes
                ep_api   = f"{self._api_url}/series/{p_id}/{s_num}"
                ep_istek = await self.httpx.get(ep_api)
                try:
                    ep_data = ep_istek.json()
                    for ep in ep_data.get("episodes", []):
                        e_num    = ep.get("number")
                        e_title  = ep.get("title") or f"Episode {e_num}"
                        e_poster = self._extract_img_src(ep.get("image", ""))
                        e_url    = ep.get("links")  # This is often the iframe or detail URL

                        episodes.append(Episode(
                            season  = int(s_num) if s_num.isdigit() else 1,
                            episode = int(e_num) if e_num and e_num.isdigit() else (len(episodes) + 1),
                            title   = e_title,
                            url     = self.fix_url(e_url),
                            poster  = e_poster
                        ))
                except Exception:
                    continue

            return SeriesInfo(
                url         = url,
                poster      = poster,
                title       = title,
                description = desc,
                tags        = tags,
                rating      = rating,
                year        = year,
                actors      = actors,
                duration    = duration,
                episodes    = episodes
            )
        else:
            return MovieInfo(
                url         = url,
                poster      = poster,
                title       = title,
                description = desc,
                tags        = tags,
                rating      = rating,
                year        = year,
                actors      = actors,
                duration    = duration
            )

    async def load_links(self, url: str) -> list[ExtractResult]:
        # url might be direct or from Episodes
        istek  = await self.httpx.get(url, headers={"Referer": self.main_url})
        secici = HTMLHelper(istek.text)

        # Look for iframe
        iframe = self.fix_url(secici.select_attr("div.embed iframe", "src"))
        if not iframe:
            return []

        # Load player wrapper
        if_istek  = await self.httpx.get(iframe, headers={"Referer": self.main_url})
        if_secici = HTMLHelper(if_istek.text)

        decoded_urls = []
        for li in if_secici.select("li[onclick]"):
            onclick = li.select_attr(None, "onclick")
            if "showVideo('" in onclick:
                encoded = re.search(r"showVideo\('([^']+)'", onclick)
                if encoded:
                    try:
                        decoded_url = base64.b64decode(encoded.group(1)).decode()
                        decoded_urls.append(self.fix_url(decoded_url))
                    except Exception:
                        pass

        results = []
        direct  = [u for u in decoded_urls if ".m3u8" in u or ".mp4" in u]
        embed   = [u for u in decoded_urls if u not in direct]

        results.extend(ExtractResult(name=self.name, url=u) for u in direct)

        tasks = [self.extract(u, referer=self.main_url) for u in embed]
        for ext in await self.gather_with_limit(tasks):
            self.collect_results(results, ext)

        return results

    def clean_title(self, title: str) -> str:
        if not title:
            return ""

        # Remove French streaming keywords and extra markers
        title = re.split(r'\s+(?:en|voir|complet|streaming|vf|vostfr|hd|vost|officiel|en ligne)', title, flags=re.I)[0]
        title = re.sub(r'^(?:Série|Film|[Aa]nimes?|[Áá]nimes?|Voir)s?[\s:]+', '', title, flags=re.U)
        title = title.split(" ✅ ")[0].strip(" :")

        return title
