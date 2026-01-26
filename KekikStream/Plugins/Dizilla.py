# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult, HTMLHelper
from json              import loads
from urllib.parse      import urlparse, urlunparse
from Crypto.Cipher     import AES
from base64            import b64decode

class Dizilla(PluginBase):
    name        = "Dizilla"
    language    = "tr"
    main_url    = "https://dizilla.to"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "1080p yabancı dizi izle. Türkçe altyazılı veya dublaj seçenekleriyle 1080p çözünürlükte yabancı dizilere anında ulaş. Popüler dizileri kesintisiz izle."

    main_page   = {
        f"{main_url}/tum-bolumler" : "Altyazılı Bölümler",
        f"{main_url}/api/bg/findSeries?releaseYearStart=1900&releaseYearEnd=2050&imdbPointMin=0&imdbPointMax=10&categoryIdsComma=15&countryIdsComma=&orderType=date_desc&languageId=-1&currentPage=SAYFA&currentPageCount=24&queryStr=&categorySlugsComma=&countryCodesComma=" : "Aile",
        f"{main_url}/api/bg/findSeries?releaseYearStart=1900&releaseYearEnd=2050&imdbPointMin=0&imdbPointMax=10&categoryIdsComma=9&countryIdsComma=&orderType=date_desc&languageId=-1&currentPage=SAYFA&currentPageCount=24&queryStr=&categorySlugsComma=&countryCodesComma="  : "Aksiyon",
        f"{main_url}/api/bg/findSeries?releaseYearStart=1900&releaseYearEnd=2050&imdbPointMin=0&imdbPointMax=10&categoryIdsComma=17&countryIdsComma=&orderType=date_desc&languageId=-1&currentPage=SAYFA&currentPageCount=24&queryStr=&categorySlugsComma=&countryCodesComma=" : "Animasyon",
        f"{main_url}/api/bg/findSeries?releaseYearStart=1900&releaseYearEnd=2050&imdbPointMin=0&imdbPointMax=10&categoryIdsComma=5&countryIdsComma=&orderType=date_desc&languageId=-1&currentPage=SAYFA&currentPageCount=24&queryStr=&categorySlugsComma=&countryCodesComma="  : "Bilim Kurgu",
        f"{main_url}/api/bg/findSeries?releaseYearStart=1900&releaseYearEnd=2050&imdbPointMin=0&imdbPointMax=10&categoryIdsComma=2&countryIdsComma=&orderType=date_desc&languageId=-1&currentPage=SAYFA&currentPageCount=24&queryStr=&categorySlugsComma=&countryCodesComma="  : "Dram",
        f"{main_url}/api/bg/findSeries?releaseYearStart=1900&releaseYearEnd=2050&imdbPointMin=0&imdbPointMax=10&categoryIdsComma=12&countryIdsComma=&orderType=date_desc&languageId=-1&currentPage=SAYFA&currentPageCount=24&queryStr=&categorySlugsComma=&countryCodesComma=" : "Fantastik",
        f"{main_url}/api/bg/findSeries?releaseYearStart=1900&releaseYearEnd=2050&imdbPointMin=0&imdbPointMax=10&categoryIdsComma=18&countryIdsComma=&orderType=date_desc&languageId=-1&currentPage=SAYFA&currentPageCount=24&queryStr=&categorySlugsComma=&countryCodesComma=" : "Gerilim",
        f"{main_url}/api/bg/findSeries?releaseYearStart=1900&releaseYearEnd=2050&imdbPointMin=0&imdbPointMax=10&categoryIdsComma=3&countryIdsComma=&orderType=date_desc&languageId=-1&currentPage=SAYFA&currentPageCount=24&queryStr=&categorySlugsComma=&countryCodesComma="  : "Gizem",
        f"{main_url}/api/bg/findSeries?releaseYearStart=1900&releaseYearEnd=2050&imdbPointMin=0&imdbPointMax=10&categoryIdsComma=4&countryIdsComma=&orderType=date_desc&languageId=-1&currentPage=SAYFA&currentPageCount=24&queryStr=&categorySlugsComma=&countryCodesComma="  : "Komedi",
        f"{main_url}/api/bg/findSeries?releaseYearStart=1900&releaseYearEnd=2050&imdbPointMin=0&imdbPointMax=10&categoryIdsComma=8&countryIdsComma=&orderType=date_desc&languageId=-1&currentPage=SAYFA&currentPageCount=24&queryStr=&categorySlugsComma=&countryCodesComma="  : "Korku",
        f"{main_url}/api/bg/findSeries?releaseYearStart=1900&releaseYearEnd=2050&imdbPointMin=0&imdbPointMax=10&categoryIdsComma=24&countryIdsComma=&orderType=date_desc&languageId=-1&currentPage=SAYFA&currentPageCount=24&queryStr=&categorySlugsComma=&countryCodesComma=" : "Macera",
        f"{main_url}/api/bg/findSeries?releaseYearStart=1900&releaseYearEnd=2050&imdbPointMin=0&imdbPointMax=10&categoryIdsComma=7&countryIdsComma=&orderType=date_desc&languageId=-1&currentPage=SAYFA&currentPageCount=24&queryStr=&categorySlugsComma=&countryCodesComma="  : "Romantik",
        f"{main_url}/api/bg/findSeries?releaseYearStart=1900&releaseYearEnd=2050&imdbPointMin=0&imdbPointMax=10&categoryIdsComma=26&countryIdsComma=&orderType=date_desc&languageId=-1&currentPage=SAYFA&currentPageCount=24&queryStr=&categorySlugsComma=&countryCodesComma=" : "Savaş",
        f"{main_url}/api/bg/findSeries?releaseYearStart=1900&releaseYearEnd=2050&imdbPointMin=0&imdbPointMax=10&categoryIdsComma=1&countryIdsComma=&orderType=date_desc&languageId=-1&currentPage=SAYFA&currentPageCount=24&queryStr=&categorySlugsComma=&countryCodesComma="  : "Suç",
        f"{main_url}/api/bg/findSeries?releaseYearStart=1900&releaseYearEnd=2050&imdbPointMin=0&imdbPointMax=10&categoryIdsComma=11&countryIdsComma=&orderType=date_desc&languageId=-1&currentPage=SAYFA&currentPageCount=24&queryStr=&categorySlugsComma=&countryCodesComma=" : "Western",
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        ana_sayfa = []

        if "api/bg" in url:
            istek     = await self.httpx.post(url.replace("SAYFA", str(page)))
            decrypted = await self.decrypt_response(istek.json().get("response"))
            veriler   = decrypted.get("result", [])
            ana_sayfa.extend([
                MainPageResult(
                    category = category,
                    title    = veri.get("original_title"),
                    url      = self.fix_url(f"{self.main_url}/{veri.get('used_slug')}"),
                    poster   = self.fix_poster_url(self.fix_url(veri.get("object_poster_url"))),
                )
                    for veri in veriler
            ])
        else:
            istek  = await self.httpx.get(url.replace("SAYFA", str(page)))
            secici = HTMLHelper(istek.text)

            # Genel olarak dizi sayfalarına giden linkleri al
            for veri in secici.select('a[href*="/dizi/"]'):
                href = secici.select_attr('a', 'href', veri)
                title = secici.select_text(None, veri)
                if not href or not title:
                    continue

                # Detay sayfasından poster vb. bilgileri al
                ep_req = await self.httpx.get(self.fix_url(href))
                ep_secici = HTMLHelper(ep_req.text)
                poster = ep_secici.select_poster('img.imgt') or ep_secici.select_poster('img')

                ana_sayfa.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster) if poster else None
                ))

        return ana_sayfa

    async def decrypt_response(self, response: str) -> dict:
        # 32 bytes key
        key = "9bYMCNQiWsXIYFWYAu7EkdsSbmGBTyUI".encode("utf-8")

        # IV = 16 bytes of zero
        iv = bytes([0] * 16)

        # Base64 decode
        encrypted_bytes = b64decode(response)

        # AES/CBC/PKCS5Padding
        cipher    = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(encrypted_bytes)

        # PKCS5/PKCS7 padding remove
        pad_len   = decrypted[-1]
        decrypted = decrypted[:-pad_len]

        # JSON decode
        return loads(decrypted.decode("utf-8"))

    def fix_poster_url(self, url: str) -> str:
        """AMP CDN URL'lerini düzelt."""
        if not url:
            return url
        # AMP CDN URL'lerini orijinal URL'ye çevir
        # https://images-macellan-online.cdn.ampproject.org/i/s/images.macellan.online/...
        # -> https://images.macellan.online/...
        if "cdn.ampproject.org" in url:
            # /i/s/ veya /ii/s/ gibi AMP prefix'lerinden sonraki kısmı al
            helper = HTMLHelper(url)
            match = helper.regex_first(r"cdn\.ampproject\.org/[^/]+/s/(.+)$")
            if match:
                return f"https://{match}"
        return url

    async def search(self, query: str) -> list[SearchResult]:
        arama_istek = await self.httpx.post(f"{self.main_url}/api/bg/searchcontent?searchterm={query}")
        decrypted   = await self.decrypt_response(arama_istek.json().get("response"))
        arama_veri  = decrypted.get("result", [])

        return [
            SearchResult(
                title  = veri.get("object_name"),
                url    = self.fix_url(f"{self.main_url}/{veri.get('used_slug')}"),
                poster = self.fix_poster_url(self.fix_url(veri.get("object_poster_url"))),
            )
                for veri in arama_veri
        ]

    async def url_base_degis(self, eski_url:str, yeni_base:str) -> str:
        parsed_url       = urlparse(eski_url)
        parsed_yeni_base = urlparse(yeni_base)
        yeni_url         = parsed_url._replace(
            scheme = parsed_yeni_base.scheme,
            netloc = parsed_yeni_base.netloc
        )

        return urlunparse(yeni_url)

    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        next_data_text = secici.select_text("script#__NEXT_DATA__")
        if not next_data_text: return None

        next_data   = loads(next_data_text)
        secure_data = next_data.get("props", {}).get("pageProps", {}).get("secureData")
        if not secure_data: return None

        decrypted = await self.decrypt_response(secure_data)
        content   = decrypted.get("contentItem", {})
        if not content: return None

        title       = content.get("original_title") or content.get("used_title")
        description = content.get("description") or content.get("used_description")
        rating      = content.get("imdb_point") or content.get("local_vote_avg")
        year        = content.get("release_year")
        poster      = self.fix_poster_url(self.fix_url(content.get("back_url") or content.get("poster_url")))

        tags   = [cat.get("name") for cat in decrypted.get("RelatedResults", {}).get("getSerieCategoriesById", {}).get("result", [])]
        actors = [cast.get("name") for cast in decrypted.get("RelatedResults", {}).get("getSerieCastsById", {}).get("result", [])]

        episodes = []
        for season in decrypted.get("RelatedResults", {}).get("getSerieSeasonAndEpisodes", {}).get("result", []):
            s_no = season.get("season_no")
            for ep in season.get("episodes", []):
                e_no = ep.get("episode_no")
                slug = ep.get("used_slug")
                name = ep.get("episode_text") or ""
                if not any(e.season == s_no and e.episode == e_no for e in episodes):
                    episodes.append(Episode(season=s_no, episode=e_no, title=name, url=self.fix_url(f"{self.main_url}/{slug}")))

        return SeriesInfo(
            url         = url,
            poster      = poster,
            title       = title or "Bilinmiyor",
            description = description,
            tags        = tags,
            rating      = str(rating) if rating else None,
            year        = str(year) if year else None,
            episodes    = episodes,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek   = await self.httpx.get(url)
        secici  = HTMLHelper(istek.text)

        next_data_text = secici.select_text("script#__NEXT_DATA__")
        if not next_data_text:
            return []

        next_data = loads(next_data_text)
        secure_data = next_data.get("props", {}).get("pageProps", {}).get("secureData", {})
        decrypted   = await self.decrypt_response(secure_data)
        results     = decrypted.get("RelatedResults", {}).get("getEpisodeSources", {}).get("result", [])

        if not results:
            return []

        # Get first source (matching Kotlin)
        first_result = results[0]
        source_content = str(first_result.get("source_content", ""))
        
        # Clean the source_content string (matching Kotlin: .replace("\"", "").replace("\\", ""))
        cleaned_source = source_content.replace('"', '').replace('\\', '')
        
        # Parse cleaned HTML
        iframe_secici = HTMLHelper(cleaned_source)
        iframe_src = iframe_secici.select_attr("iframe", "src")
        
        # Referer check (matching Kotlin: loadExtractor(iframe, "${mainUrl}/", ...))
        iframe_url = self.fix_url(iframe_src) if iframe_src else None
        
        if not iframe_url:
            return []

        data = await self.extract(iframe_url, referer=f"{self.main_url}/", prefix=first_result.get('language_name', 'Unknown'))
        if not data:
            return []
        return data if isinstance(data, list) else [data]
