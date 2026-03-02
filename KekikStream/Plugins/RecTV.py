# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, Episode, SeriesInfo, ExtractResult, HTMLHelper
from json             import dumps, loads
import re, contextlib

def _decode_unicode(text: str | None) -> str | None:
    """API'den gelen backslash'sız unicode escape'leri çözer (ör. u00c7 → Ç)."""
    if not isinstance(text, str):
        return text
    return re.sub(r'(?<![\\])u([0-9a-fA-F]{4})', lambda m: chr(int(m.group(1), 16)), text)

class RecTV(PluginBase):
    name        = "RecTV"
    language    = "tr"
    main_url    = "https://a.prectv67.lol"
    favicon     = "https://rectvapk.cc/wp-content/uploads/2023/02/Rec-TV.webp"
    description = "RecTv APK, Türkiye’deki en popüler Çevrimiçi Medya Akış platformlarından biridir. Filmlerin, Canlı Sporların, Web Dizilerinin ve çok daha fazlasının keyfini ücretsiz çıkarın."

    sw_key = "4F5A9C3D9A86FA54EACEDDD635185/c3c5bd17-e37b-4b94-a944-8a3688a30452"

    main_page   = {
        f"{main_url}/api/channel/by/filtres/0/0/SAYFA/{sw_key}/"      : "Canlı",
        f"{main_url}/api/movie/by/filtres/0/created/SAYFA/{sw_key}/"  : "Son Filmler",
        f"{main_url}/api/serie/by/filtres/0/created/SAYFA/{sw_key}/"  : "Son Diziler",
        f"{main_url}/api/movie/by/filtres/26/created/SAYFA/{sw_key}/" : "Türkçe Dublaj",
        f"{main_url}/api/movie/by/filtres/27/created/SAYFA/{sw_key}/" : "Türkçe Altyazı",
        f"{main_url}/api/movie/by/filtres/42/created/SAYFA/{sw_key}/" : "Şarj Bitiren İçerikler",
        f"{main_url}/api/movie/by/filtres/20/created/SAYFA/{sw_key}/" : "Ödüllü Filmler",
        f"{main_url}/api/movie/by/filtres/1/created/SAYFA/{sw_key}/"  : "Aksiyon",
        f"{main_url}/api/movie/by/filtres/2/created/SAYFA/{sw_key}/"  : "Dram",
        f"{main_url}/api/movie/by/filtres/3/created/SAYFA/{sw_key}/"  : "Komedi",
        f"{main_url}/api/movie/by/filtres/4/created/SAYFA/{sw_key}/"  : "Bilim Kurgu",
        f"{main_url}/api/movie/by/filtres/5/created/SAYFA/{sw_key}/"  : "Romantik",
        f"{main_url}/api/movie/by/filtres/7/created/SAYFA/{sw_key}/"  : "Polisiye - Suç",
        f"{main_url}/api/movie/by/filtres/8/created/SAYFA/{sw_key}/"  : "Korku",
        f"{main_url}/api/movie/by/filtres/9/created/SAYFA/{sw_key}/"  : "Gerilim",
        f"{main_url}/api/movie/by/filtres/10/created/SAYFA/{sw_key}/" : "Fantastik",
        f"{main_url}/api/movie/by/filtres/13/created/SAYFA/{sw_key}/" : "Animasyon",
        f"{main_url}/api/movie/by/filtres/14/created/SAYFA/{sw_key}/" : "Aile",
        f"{main_url}/api/movie/by/filtres/15/created/SAYFA/{sw_key}/" : "Gizem",
        f"{main_url}/api/movie/by/filtres/16/created/SAYFA/{sw_key}/" : "Heyecan",
        f"{main_url}/api/movie/by/filtres/17/created/SAYFA/{sw_key}/" : "Macera",
        f"{main_url}/api/movie/by/filtres/19/created/SAYFA/{sw_key}/" : "Belgesel",
        f"{main_url}/api/movie/by/filtres/21/created/SAYFA/{sw_key}/" : "Tarih",
        f"{main_url}/api/movie/by/filtres/22/created/SAYFA/{sw_key}/" : "Suç",
        f"{main_url}/api/movie/by/filtres/24/created/SAYFA/{sw_key}/" : "Müzik",
        f"{main_url}/api/movie/by/filtres/25/created/SAYFA/{sw_key}/" : "Western",
        f"{main_url}/api/movie/by/filtres/32/created/SAYFA/{sw_key}/" : "Savaş",
        f"{main_url}/api/movie/by/filtres/34/created/SAYFA/{sw_key}/" : "Çocuklar",
    }

    async def _make_headers(self, method: str, path: str, body: bytes = b"") -> dict:
        try:
            response = await self.httpx.get(f"http://10.0.0.2:2585/api/v1/rectv?method={method}&path={path}&body={body.decode() if body else ''}")
            veriler  = response.json()
            if veriler.get("success"):
                headers = veriler.get("headers")
                headers.update({"User-Agent": "okhttp/4.12.0"})
                return headers
        except Exception:
            pass

        return {"User-Agent": "okhttp/4.12.0"}

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        target_url = url.replace('SAYFA', str(int(page) - 1))
        path       = target_url.replace(self.main_url, "")

        headers = await self._make_headers("GET", path)
        istek   = await self.httpx.get(target_url, headers=headers)
        veriler = istek.json()

        return [
            MainPageResult(
                category = category,
                title    = veri.get("title"),
                url      = dumps(veri),
                poster   = self.fix_url(veri.get("image")),
            )
                for veri in veriler
        ]

    async def search(self, query: str) -> list[SearchResult]:
        path = f"/api/search/{query}/{self.sw_key}/"

        headers = await self._make_headers("GET", path)
        istek   = await self.httpx.get(f"{self.main_url}{path}", headers=headers)

        kanallar  = istek.json().get("channels")
        icerikler = istek.json().get("posters")
        tum_veri  = {item['title']: item for item in kanallar + icerikler}.values()
        tum_veri  = sorted(tum_veri, key=lambda sozluk: sozluk["title"])

        tur_ver   = lambda veri: " | Dizi" if veri.get("type") == "serie" else " | Film"

        return [
            SearchResult(
                title  = veri.get("title") + tur_ver(veri),
                url    = dumps(veri),
                poster = self.fix_url(veri.get("image")),
            )
                for veri in tum_veri
        ]

    async def load_item(self, url: str) -> MovieInfo | SeriesInfo:
        veri = loads(url)

        # Süreyi dakikaya çevir (Örn: "1h 59min")
        duration_raw = veri.get("duration")
        duration     = None
        if duration_raw:
            with contextlib.suppress(Exception):
                h = int(HTMLHelper(duration_raw).regex_first(r"(\d+)h") or 0)
                m = int(HTMLHelper(duration_raw).regex_first(r"(\d+)min") or 0)
                duration = h * 60 + m

        common_info = {
            "url"         : url,
            "poster"      : self.fix_url(veri.get("image")),
            "title"       : _decode_unicode(veri.get("title")),
            "description" : _decode_unicode(veri.get("description")),
            "tags"        : [genre.get("title") for genre in veri.get("genres")] if veri.get("genres") else [],
            "rating"      : str(veri.get("imdb") or veri.get("rating") or ""),
            "year"        : str(veri.get("year") or ""),
            "duration"    : duration
        }

        if veri.get("type") == "serie":
            path = f"/api/season/by/serie/{veri.get('id')}/{self.sw_key}/"

            headers    = await self._make_headers("GET", path)
            dizi_istek = await self.httpx.get(f"{self.main_url}{path}", headers=headers)
            dizi_veri  = dizi_istek.json()

            episodes = []
            for season in dizi_veri:
                s_title = season.get("title", "").strip()
                s, _    = HTMLHelper.extract_season_episode(s_title)
                for ep in season.get("episodes"):
                    e_title = ep.get("title", "").strip()
                    _, e    = HTMLHelper.extract_season_episode(e_title)
                    for source in ep.get("sources"):
                        tag     = ""
                        clean_s = s_title
                        if "dublaj" in s_title.lower():
                            tag = " (Dublaj)"; clean_s = re.sub(r"\s*dublaj\s*", "", s_title, flags=re.I).strip()
                        elif "altyaz" in s_title.lower():
                            tag = " (Altyazı)"; clean_s = re.sub(r"\s*altyaz[ıi]\s*", "", s_title, flags=re.I).strip()

                        ep_data = {"url": self.fix_url(source.get("url")), "title": source.get("title"), "is_episode": True}
                        episodes.append(Episode(
                            season  = s or 1,
                            episode = e or 1,
                            title   = f"{clean_s} {e_title}{tag} - {source.get('title')}",
                            url     = dumps(ep_data)
                        ))

            return SeriesInfo(**common_info, episodes=episodes, actors=[])

        return MovieInfo(**common_info, actors=[])

    async def load_links(self, url: str) -> list[ExtractResult]:
        try:
            veri = loads(url)
        except Exception:
            # JSON değilse düz URL'dir (eski yapı veya hata)
            return [ExtractResult(url=url, name="Video")]

        # Eğer dizi bölümü ise (bizim oluşturduğumuz yapı)
        if veri.get("is_episode"):
            return [ExtractResult(
                url        = veri.get("url"),
                name       = _decode_unicode(veri.get("title", "Video")),
                user_agent = "googleusercontent",
                referer    = "https://twitter.com/"
            )]

        # Film ise (RecTV API yapısı)
        results = []
        if veri.get("sources"):
            for kaynak in veri.get("sources"):
                video_link = kaynak.get("url")
                if "otolinkaff" in video_link:
                    continue

                results.append(ExtractResult(
                    url        = video_link,
                    name       = _decode_unicode(kaynak.get("title", "Video")),
                    user_agent = "googleusercontent",
                    referer    = "https://twitter.com/"
                ))

        return results
