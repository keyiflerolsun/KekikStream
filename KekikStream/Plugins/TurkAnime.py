# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
from Kekik.Sifreleme  import AESManager
import re, base64

class TurkAnime(PluginBase):
    name        = "TurkAnime"
    language    = "tr"
    main_url    = "https://www.turkanime.tv"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Türk Anime TV - Türkiye'nin Online Anime izleme sitesi."

    main_page   = {
        f"{main_url}/anime-turu/1/Aksiyon"    : "Aksiyon",
        f"{main_url}/anime-turu/8/Dram"       : "Dram",
        f"{main_url}/anime-turu/10/Fantastik" : "Fantastik",
        f"{main_url}/anime-turu/4/Komedi"     : "Komedi",
        f"{main_url}/anime-turu/14/Korku"     : "Korku",
        f"{main_url}/anime-turu/2/Macera"     : "Macera",
        f"{main_url}/anime-turu/22/Romantizm" : "Romantizm",
        f"{main_url}/anime-turu/27/Shounen"   : "Shounen",
        f"{main_url}/anime-turu/30/Spor"      : "Spor",
    }

    _AES_KEY    = "710^8A@3@>T2}#zN5xK?kR7KNKb@-A!LzYL5~M1qU0UfdWsZoBm4UUat%}ueUv6E--*hDPPbH7K2bp9^3o41hw,khL:}Kx8080@M"
    _CSRF_TOKEN = "EqdGHqwZJvydjfbmuYsZeGvBxDxnQXeARRqUNbhRYnPEWqdDnYFEKVBaUPCAGTZA"
    _COOKIES    = {"yasOnay": "1"}

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(url, cookies=self._COOKIES)
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("div#orta-icerik div.panel"):
            title  = veri.select_text("div.panel-title a")
            href   = veri.select_attr("div.panel-title a", "href")
            poster = veri.select_attr("img", "data-src")

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title.strip(),
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek = await self.httpx.post(
            f"{self.main_url}/arama",
            data    = {"arama": query},
            cookies = self._COOKIES,
        )

        # Sonuçlar AJAX ile yükleniyor; encoded arama URL'sini çıkar
        ajax_match = re.search(r"ajax/arama&aranan=([^&'\"]+)", istek.text)
        if not ajax_match:
            return []

        ajax_url  = f"{self.main_url}/{ajax_match.group(0)}"
        ajax_resp = await self.httpx.get(
            ajax_url,
            headers = {"X-Requested-With": "XMLHttpRequest"},
            cookies = self._COOKIES,
        )

        # Tek sonuç varsa site JS ile yönlendiriyor: window.location = "anime/..."
        redirect_match = re.search(r'window\.location\s*=\s*"([^"]+)"', ajax_resp.text)
        if redirect_match:
            redirect_url = self.fix_url(redirect_match.group(1))
            # Yönlendirilen sayfadan bilgileri çek
            try:
                detail = await self.httpx.get(redirect_url, cookies=self._COOKIES)
                dsecici = HTMLHelper(detail.text)
                title   = dsecici.select_text("div#detayPaylas div.panel-title") or redirect_url.rstrip("/").split("/")[-1]
                poster  = dsecici.select_attr("div#detayPaylas div.imaj img", "data-src")
                return [SearchResult(
                    title  = title.strip(),
                    url    = redirect_url,
                    poster = self.fix_url(poster),
                )]
            except Exception:
                return [SearchResult(title=redirect_url.rstrip("/").split("/")[-1], url=redirect_url, poster=None)]

        secici = HTMLHelper(ajax_resp.text)

        results = []
        for veri in secici.select("div.panel"):
            title  = veri.select_text("div.panel-title a")
            href   = veri.select_attr("div.panel-title a", "href")
            poster = veri.select_attr("img", "data-src")

            if title and href and "/anime/" in href:
                results.append(SearchResult(
                    title  = title.strip(),
                    url    = self.fix_url(href),
                    poster = self.fix_url(poster),
                ))

        return results

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url, cookies=self._COOKIES)
        secici = HTMLHelper(istek.text)

        title       = secici.select_text("div#detayPaylas div.panel-title") or ""
        poster      = secici.select_attr("div#detayPaylas div.imaj img", "data-src")
        description = secici.select_text("div#detayPaylas p.ozet")
        tags        = secici.select_texts("div#animedetay a[href*='anime-turu']")

        year = None
        year_el = secici.select_attr("div#detayPaylas a[href*='yil/']", "href")
        if year_el:
            y_match = re.search(r"yil/(\d+)", year_el)
            if y_match:
                year = y_match.group(1)

        # _token meta tag
        token = secici.select_attr("meta[name='_token']", "content") or ""

        # Bölüm listesi ajax URL'i
        bolumler_url = secici.select_attr("a[data-url*='ajax/bolumler']", "data-url")
        episodes = []

        if bolumler_url:
            bolumler_url = self.fix_url(bolumler_url)
            bol_resp = await self.httpx.get(
                bolumler_url,
                headers = {
                    "X-Requested-With" : "XMLHttpRequest",
                    "token"            : token,
                },
                cookies = self._COOKIES,
            )
            bol_secici = HTMLHelper(bol_resp.text)

            for li in bol_secici.select("div#bolum-list li"):
                ep_href  = li.select_attr("a[href*='/video/']", "href")
                ep_name  = li.select_text("span.bolumAdi")
                ep_title = li.select_attr("a[href*='/video/']", "title") or ""

                if not ep_href:
                    continue

                ep_num = 1
                ep_match = re.search(r"(\d+)\.\s*Bölüm", ep_title)
                if ep_match:
                    ep_num = int(ep_match.group(1))

                episodes.append(Episode(
                    season  = 1,
                    episode = ep_num,
                    title   = ep_name or f"Bölüm {ep_num}",
                    url     = self.fix_url(ep_href),
                ))

        return SeriesInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title.strip(),
            description = description,
            tags        = tags,
            year        = year,
            episodes    = episodes,
        )

    def _iframe_to_aes_link(self, iframe: str) -> str | None:
        """iframe embed URL'den AES şifreli veriyi çöz → gerçek URL"""
        try:
            aes_data = iframe.split("embed/#/url/")[1].split("?status")[0] if "embed/#/url/" in iframe else ""
            if not aes_data:
                return None

            aes_data = base64.b64decode(aes_data).decode("utf-8")
            result   = AESManager.decrypt(aes_data, self._AES_KEY)

            if result:
                result = result.replace("\\", "").replace('"', "").strip()
                return self.fix_url(result)
        except Exception:
            pass

        return None

    async def _player_sources(self, player_url: str) -> list[ExtractResult]:
        """turkanime.tv/player/<hash> URL'sinden sources API ile video çek."""
        results = []
        try:
            # Hash'i URL'den çıkar
            player_hash = player_url.rstrip("/").split("/player/")[-1]
            if not player_hash:
                return results

            # Player sayfasını GET (apiURL doğrulaması)
            player_resp = await self.httpx.get(
                f"{self.main_url}/player/{player_hash}",
                headers = {"Referer": f"{self.main_url}/"},
                cookies = self._COOKIES,
            )

            # apiURL'yi HTML'den çek (doğrulama)
            api_match = re.search(r"apiURL\s*=\s*'([^']+)'", player_resp.text)
            if not api_match:
                return results

            api_url = api_match.group(1)

            # Sources API çağır
            src_resp = await self.httpx.get(
                f"{api_url}true",
                headers = {
                    "Referer"          : f"{self.main_url}/player/{player_hash}",
                    "X-Requested-With" : "XMLHttpRequest",
                    "Csrf-Token"       : self._CSRF_TOKEN,
                },
                cookies = self._COOKIES,
            )

            data = src_resp.json()
            resp_data = data.get("response", {})
            if not resp_data.get("status"):
                return results

            sources = resp_data.get("sources", [])
            for src in sources:
                file_url = src.get("file", "")
                if file_url:
                    file_url = self.fix_url(file_url)
                    label    = src.get("label", "")
                    results.append(ExtractResult(
                        name    = label or "Kaynak",
                        url     = file_url,
                        referer = f"{self.main_url}/",
                    ))

            # Altyazı varsa ekle
            tracks = resp_data.get("track", [])
            for track in tracks:
                sub_file = track.get("file", "")
                if sub_file and sub_file.strip():
                    for res in results:
                        res.subtitles = res.subtitles or []
                        res.subtitles.append(self.new_subtitle(
                            name = track.get("label", track.get("kind", "Altyazı")),
                            url  = self.fix_url(sub_file),
                        ))
        except Exception:
            pass

        return results

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url, cookies=self._COOKIES)
        secici = HTMLHelper(istek.text)

        response = []

        # Artplayer data-url veya iframe kontrol
        iframe_src  = secici.select_attr("iframe", "src")
        is_ad       = iframe_src and "a-ads.com" in iframe_src

        # button onclick → ajax/videosec → alternatif kaynaklar
        sub_links = []
        for button in secici.select("button[onclick*='ajax/videosec']"):
            onclick = button.attrs.get("onclick", "")
            if not onclick:
                continue
            sub_link_match = re.search(r"IndexIcerik\('([^']+)'", onclick)
            if sub_link_match:
                sub_links.append(self.fix_url(sub_link_match.group(1)))

        async def _process_sub_link(sub_link):
            try:
                sub_resp   = await self.httpx.get(
                    sub_link,
                    headers = {
                        "X-Requested-With" : "XMLHttpRequest",
                        "Referer"          : url,
                    },
                    cookies = self._COOKIES,
                )
                sub_secici = HTMLHelper(sub_resp.text)

                # Artplayer data-url kontrol (m3u8 direkt link)
                data_url = sub_secici.select_attr("div.artplayer-app", "data-url")
                if data_url and data_url.endswith(".m3u8"):
                    return [ExtractResult(name="TurkAnime", url=data_url, referer=sub_link)]

                # İframe → AES decode → extractor veya internal player
                sub_iframe = sub_secici.select_attr("iframe", "src")
                if sub_iframe:
                    real_url = self._iframe_to_aes_link(sub_iframe)
                    if real_url:
                        if "turkanime.tv/player/" in real_url:
                            return await self._player_sources(real_url)
                        else:
                            data = await self.extract(real_url, referer=f"{self.main_url}/")
                            return [data] if data else []
            except Exception:
                pass
            return []

        all_results = await self.gather_with_limit([_process_sub_link(link) for link in sub_links])
        for result_list in all_results:
            if result_list:
                response.extend(result_list)

        # İlk iframe (reklam değilse)
        if iframe_src and not is_ad:
            real_url = self._iframe_to_aes_link(iframe_src)
            if real_url:
                if "turkanime.tv/player/" in real_url:
                    player_results = await self._player_sources(real_url)
                    response.extend(player_results)
                else:
                    data = await self.extract(real_url, referer=f"{self.main_url}/")
                    self.collect_results(response, data)

        return self.deduplicate(response)
