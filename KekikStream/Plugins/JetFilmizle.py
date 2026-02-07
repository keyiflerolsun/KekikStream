# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, SeriesInfo, Episode, ExtractResult, HTMLHelper
import json, re
from urllib.parse import urlparse, parse_qs

class JetFilmizle(PluginBase):
    name        = "JetFilmizle"
    language    = "tr"
    main_url    = "https://jetfilmizle.net"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Filmler: En yeni yerli ve yabancı yapımları Full HD kalitede izle. Türkçe dublaj ve altyazı seçenekleriyle sunulan ödüllü sinema eserlerini JetFilmizle hızıyla keşfedin."

    main_page = {
        f"{main_url}/filmler/sayfa-"              : "Filmler",
        f"{main_url}/diziler/sayfa-"              : "Diziler",
        f"{main_url}/tur/aile/sayfa-"             : "Aile",
        f"{main_url}/tur/aksiyon/sayfa-"          : "Aksiyon",
        f"{main_url}/tur/animasyon/sayfa-"        : "Animasyon",
        f"{main_url}/tur/anime/sayfa-"            : "Anime",
        f"{main_url}/tur/belgesel/sayfa-"         : "Belgesel",
        f"{main_url}/tur/bilim-kurgu/sayfa-"      : "Bilim Kurgu",
        f"{main_url}/tur/biyografi/sayfa-"        : "Biyografi",
        f"{main_url}/tur/casus/sayfa-"            : "Casus",
        f"{main_url}/tur/dram/sayfa-"             : "Dram",
        f"{main_url}/tur/fantastik/sayfa-"        : "Fantastik",
        f"{main_url}/tur/fantezi/sayfa-"          : "Fantezi",
        f"{main_url}/tur/felaket/sayfa-"          : "Felaket",
        f"{main_url}/tur/gerilim/sayfa-"          : "Gerilim",
        f"{main_url}/tur/gizem/sayfa-"            : "Gizem",
        f"{main_url}/tur/komedi/sayfa-"           : "Komedi",
        f"{main_url}/tur/korku/sayfa-"            : "Korku",
        f"{main_url}/tur/macera/sayfa-"           : "Macera",
        f"{main_url}/tur/muzik/sayfa-"            : "Müzik",
        f"{main_url}/tur/muzikal/sayfa-"          : "Müzikal",
        f"{main_url}/tur/reality/sayfa-"          : "Reality",
        f"{main_url}/tur/romantik/sayfa-"         : "Romantik",
        f"{main_url}/tur/savas/sayfa-"            : "Savaş",
        f"{main_url}/tur/spor/sayfa-"             : "Spor",
        f"{main_url}/tur/suc/sayfa-"              : "Suç",
        f"{main_url}/tur/tarihi/sayfa-"           : "Tarihi",
        f"{main_url}/tur/western/sayfa-"          : "Western"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}{page}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.film-card"):
            link_tag = secici.select_first("h2.card-title a", veri) or secici.select_first("a.text-decoration-none", veri)
            if not link_tag:
                continue

            title = link_tag.attrs.get("title", "").replace(" Full HD Türkçe Dublaj İzle", "").replace(" izle", "").strip()
            if not title:
                title = link_tag.text(strip=True)

            href = link_tag.attrs.get("href")

            img_tag = secici.select_first("img.card-img-top", veri)
            poster  = img_tag.attrs.get("src") or img_tag.attrs.get("data-src") if img_tag else None

            results.append(MainPageResult(
                category = category,
                title    = self.clean_title(title),
                url      = self.fix_url(href),
                poster   = self.fix_url(poster)
            ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek = await self.httpx.get(
            url     = f"{self.main_url}/arama-json",
            params  = {"q": query},
            headers = {
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"{self.main_url}/"
            }
        )

        try:
            data = istek.json()
        except:
            return []

        results = []
        for item in data.get("results", []):
            results.append(SearchResult(
                title  = self.clean_title(item.get("title")),
                url    = self.fix_url(item.get("url")),
                poster = self.fix_url(item.get("poster"))
            ))

        return results

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = self.clean_title(secici.select_text("h1"))
        poster      = secici.select_poster("div.film-poster-container img") or secici.select_poster("div.film-poster img")

        # Metadata Extraction (Specific Selectors from Debug)
        player_tag = secici.select_first("#active-player")
        rating     = player_tag.attrs.get("data-film-rating") if player_tag else secici.meta_value("IMDb")
        year       = player_tag.attrs.get("data-film-year") if player_tag else secici.meta_value("Yıl")
        duration   = secici.extract_duration("Süre")

        description = secici.select_text("div.description-text") or secici.select_text("div.film-description div.description-text") or secici.select_text("div.movie-description")

        # Tags and Actors cleanup
        tags_list   = secici.select_texts("div.categories-container-details a") or secici.meta_list("Kategoriler")
        tags_list   = [t for t in tags_list if t not in ["Kategoriler", "Tür", "Türler"]]

        actors_list = secici.select_texts("div.actors-grid .h6 a") or secici.meta_list("Oyuncular")
        actors_list = [a for a in actors_list if a not in ["Oyuncular", "Oyuncular:"]]

        # Film ID
        film_id = secici.select_attr("input[name='film_id']", "value")

        episodes = []
        # Case 1: Episode buttons in player-sources (New Structure)
        source_groups = secici.select("div.player-sources-group")
        for group in source_groups:
            p_group = group.attrs.get("data-player-group")
            for btn in secici.select("button.player-source-btn", group):
                label   = btn.text(strip=True)
                s_index = btn.attrs.get("data-source-index")

                # e.g. "1S3B" -> Season 1, Episode 3
                match = re.search(r"(\d+)S(\d+)B", label)
                if match:
                    s, e = match.groups()
                    episodes.append(Episode(
                        season  = int(s),
                        episode = int(e),
                        title   = label,
                        url     = f"{url}?film_id={film_id}&episode={s_index}&type={p_group}"
                    ))
                elif ("/dizi/" in url or "/bolum/" in url) and label.isdigit():
                    episodes.append(Episode(
                        season  = 1,
                        episode = int(label),
                        title   = f"{label}. Bölüm",
                        url     = f"{url}?film_id={film_id}&episode={s_index}&type={p_group}"
                    ))

        # Case 2: Traditional season links fallback
        if not episodes:
            for link in secici.select("div.seasons-container a[href*='/bolum/']"):
                href = link.attrs.get("href", "")
                s, e = secici.extract_season_episode(href)
                if s and e:
                    episodes.append(Episode(
                        season  = s,
                        episode = e,
                        title   = link.text(strip=True),
                        url     = self.fix_url(href)
                    ))

        if episodes or "/dizi/" in url:
            if episodes: episodes.sort(key=lambda x: (x.season, x.episode))
            return SeriesInfo(
                url         = url,
                poster      = self.fix_url(poster),
                title       = title,
                description = description,
                year        = year,
                rating      = rating,
                tags        = tags_list,
                actors      = actors_list,
                duration    = duration,
                episodes    = episodes
            )

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            year        = year,
            rating      = rating,
            tags        = tags_list,
            actors      = actors_list,
            duration    = duration,
            data        = {"film_id": film_id} if film_id else None
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)

        target_id   = params.get("film_id", [None])[0]
        target_epis = params.get("episode", [None])[0]
        target_type = params.get("type", [None])[0]

        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        film_id = target_id or secici.select_attr("input[name='film_id']", "value")
        if not film_id:
            return []

        response = []
        for btn in secici.select("button.player-source-btn"):
            p_type  = btn.attrs.get("data-player-type") or btn.attrs.get("data-player-group")
            s_index = btn.attrs.get("data-source-index")
            label   = btn.text(strip=True)

            # Episode filtering for series
            if target_epis is not None and (s_index != target_epis or p_type != target_type):
                continue

            oyun_istek = await self.httpx.post(
                url     = f"{self.main_url}/jetplayer",
                data    = {
                    "film_id": film_id,
                    "source_index": s_index,
                    "player_type": p_type
                },
                headers = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": url
                }
            )

            if oyun_istek.status_code == 200:
                iframe_secici = HTMLHelper(oyun_istek.text)
                src = iframe_secici.select_attr("iframe", "src")
                if src:
                    src = self.fix_url(src)
                    prefix = f"[{p_type.upper()}] {label}"
                    data = await self.extract(src, prefix=prefix)
                    if data:
                        if isinstance(data, list):
                            response.extend(data)
                        else:
                            response.append(data)

        return response
