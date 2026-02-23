# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper
import re, json

class FilmKovasi(PluginBase):
    name        = "FilmKovasi"
    language    = "tr"
    main_url    = "https://filmkovasi.pw"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Film Kovasi ⚡ ile en güncel ve sorunsuz Full HD Film izle keyfi her yerde seninle! 1080p online film izleme ayrıcalığıyla Film Kovası'nın Tadını Çıkarın."

    main_page   = {
        f"{main_url}/filmizle/aile/"         : "Aile",
        f"{main_url}/filmizle/aksiyon-hd/"   : "Aksiyon",
        f"{main_url}/filmizle/animasyon/"    : "Animasyon",
        f"{main_url}/filmizle/belgesel-hd/"  : "Belgesel",
        f"{main_url}/filmizle/bilim-kurgu/"  : "Bilim Kurgu",
        f"{main_url}/filmizle/dram-hd/"      : "Dram",
        f"{main_url}/filmizle/fantastik-hd/" : "Fantastik",
        f"{main_url}/filmizle/gerilim/"      : "Gerilim",
        f"{main_url}/filmizle/gizem/"        : "Gizem",
        f"{main_url}/filmizle/komedi-hd/"    : "Komedi",
        f"{main_url}/filmizle/korku/"        : "Korku",
        f"{main_url}/filmizle/macera-hd/"    : "Macera",
        f"{main_url}/filmizle/romantik-hd/"  : "Romantik",
        f"{main_url}/filmizle/savas-hd/"     : "Savaş",
        f"{main_url}/filmizle/suc-hd/"       : "Suç",
        f"{main_url}/filmizle/tarih/"        : "Tarih",
        f"{main_url}/filmizle/vahsi-bati-hd/" : "Vahşi Batı",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(f"{url}page/{page}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movie-box"):
            title  = (veri.select_text("div.film-ismi a") or "").replace(" izle", "")
            href   = veri.select_attr("div.film-ismi a", "href")
            poster = veri.select_attr("div.poster img", "data-src")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/?s={query}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div.movie-box"):
            title  = (veri.select_text("div.film-ismi a") or "").replace(" izle", "")
            href   = veri.select_attr("div.film-ismi a", "href")
            poster = veri.select_attr("div.poster img", "data-src")

            if title and href:
                results.append(SearchResult(
                    title  = title,
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> MovieInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        title       = (secici.select_text("h1.title-border") or "").replace(" izle", "").strip()
        poster      = secici.select_attr("div.film-afis img", "src")
        description = secici.select_text("div  #film-aciklama")
        tags        = secici.select_texts("div  #listelements a")
        actors      = secici.select_texts("div.actor a")

        year   = None
        rating = None

        for item in secici.select("div.list-item"):
            link_href = item.select_attr("a", "href") or ""
            if "/yil/" in link_href:
                year = item.select_text("a")
            if "/oyuncu/" in link_href:
                actors = [a.text(strip=True) for a in item.select("a")]

        for el in secici.select("div#listelements div"):
            text = el.text()
            if "IMDb:" in text:
                rating = text.strip().split()[-1]

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            year        = year,
            actors      = actors,
            rating      = rating,
        )

    @staticmethod
    def _add_marks(text: str, key: str) -> str:
        """JSON anahtarlarına tırnak ekle."""
        return re.sub(rf'"?{key}"?', f'"{key}"', text)

    async def _extract_custom_player(self, iframe_url: str) -> ExtractResult | None:
        """FilmKovası özel player — template URL + video JSON."""
        try:
            base_url = iframe_url.split("/watch/")[0] if "/watch/" in iframe_url else iframe_url.rsplit("/", 1)[0]
            i_resp   = await self.httpx.get(iframe_url, headers={"Referer": iframe_url})
            secici   = HTMLHelper(i_resp.text)

            script = ""
            for sc in secici.select("script"):
                if "sources:" in sc.text():
                    script = sc.text()
                    break

            if not script:
                return None

            # var video = {...}  →  uid, md5, id, status
            vid_json_str = script.split("var video = ", 1)[-1].split(";", 1)[0].strip()
            video_data   = json.loads(vid_json_str)

            # sources: [{file: `...`, type: "...", preload: "..."}]
            source_str = script.split("sources: [", 1)[-1].split("],", 1)[0].strip()
            source_str = self._add_marks(source_str, "file")
            source_str = self._add_marks(source_str, "type")
            source_str = self._add_marks(source_str, "preload")

            file_template = re.search(r'"file"\s*:\s*"([^"]+)"', source_str)
            if not file_template:
                return None

            file_path = file_template.group(1)
            # ${video.uid} gibi değişkenleri değiştir
            file_path = file_path.replace("${video.uid}", str(video_data.get("uid", "")))
            file_path = file_path.replace("${video.md5}", str(video_data.get("md5", "")))
            file_path = file_path.replace("${video.id}", str(video_data.get("id", "")))
            file_path = file_path.replace("${video.status}", str(video_data.get("status", "")))

            son_link = base_url + file_path

            # tracks: [{file: "...", label: "...", kind: "..."}]
            subtitle   = None
            tracks_raw = script.split("tracks: [", 1)[-1].split("]", 1)[0].strip() if "tracks: [" in script else ""
            if tracks_raw:
                tracks_raw = self._add_marks(tracks_raw, "file")
                tracks_raw = self._add_marks(tracks_raw, "label")
                tracks_raw = self._add_marks(tracks_raw, "kind")
                track_file = re.search(r'"file"\s*:\s*"([^"]+)"', tracks_raw)
                if track_file:
                    subtitle = self.new_subtitle(track_file.group(1), "Türkçe Altyazı")

            result = ExtractResult(name=self.name, url=son_link, referer=iframe_url)
            if subtitle:
                result.subtitles.append(subtitle)

            return result
        except Exception:
            return None

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        response = []

        # Ana iframe
        iframe_src = secici.select_attr("iframe", "src")
        if iframe_src:
            iframe_url = self.fix_url(iframe_src)
            # YouTube atla
            if "youtube.com" not in iframe_url:
                data = await self._extract_custom_player(iframe_url)
                if not data:
                    data = await self.extract(iframe_url, referer=f"{self.main_url}/")
                self.collect_results(response, data)

        # Alternatif kaynaklar
        async def _process_alt(alt_href):
            try:
                alt_resp   = await self.httpx.get(self.fix_url(alt_href))
                alt_secici = HTMLHelper(alt_resp.text)
                alt_iframe = alt_secici.select_attr("iframe", "src")
                if alt_iframe:
                    alt_url = self.fix_url(alt_iframe)
                    if "youtube.com" not in alt_url:
                        data = await self._extract_custom_player(alt_url)
                        if not data:
                            data = await self.extract(alt_url, referer=f"{self.main_url}/")
                        return data
            except Exception:
                pass
            return None

        alt_hrefs = [link.attrs.get("href", "") for link in secici.select("div.sources a") if link.attrs.get("href", "")]
        tasks     = [_process_alt(href) for href in alt_hrefs]
        for data in await self.gather_with_limit(tasks):
            self.collect_results(response, data)

        return response
