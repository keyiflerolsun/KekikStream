# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode, ExtractResult
from selectolax.parser import HTMLParser
from json              import loads
from urllib.parse      import urlparse, urlunparse
from Crypto.Cipher     import AES
from base64            import b64decode

class Dizilla(PluginBase):
    name        = "Dizilla"
    language    = "tr"
    main_url    = "https://dizilla40.com"
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
                    poster   = self.fix_url(veri.get("object_poster_url")),
                )
                    for veri in veriler
            ])
        else:
            istek  = await self.httpx.get(url.replace("SAYFA", str(page)))
            secici = HTMLParser(istek.text)

            for veri in secici.css("div.tab-content > div.grid a"):
                h2_el = veri.css_first("h2")
                name  = h2_el.text(strip=True) if h2_el else None

                # opacity-80 div'den episode bilgisi - normalize-space yerine doğrudan text
                opacity_el = veri.css_first("div[class*='opacity-80']")
                ep_name = opacity_el.text(strip=True) if opacity_el else None
                if not ep_name:
                    continue

                ep_name = ep_name.replace(". Sezon", "x").replace(". Bölüm", "").replace("x ", "x")
                title   = f"{name} - {ep_name}"

                href = veri.attrs.get("href")
                ep_req    = await self.httpx.get(self.fix_url(href))
                ep_secici = HTMLParser(ep_req.text)

                # nav li'leri alıp 3. elemana erişme (nth-of-type yerine)
                nav_lis = ep_secici.css("nav li")
                if len(nav_lis) >= 3:
                    link_el = nav_lis[2].css_first("a")
                    href = link_el.attrs.get("href") if link_el else None
                else:
                    href = None

                poster_el = ep_secici.css_first("img.imgt")
                poster = poster_el.attrs.get("src") if poster_el else None

                if href:
                    ana_sayfa.append(
                        MainPageResult(
                            category = category,
                            title    = title,
                            url      = self.fix_url(href),
                            poster   = self.fix_url(poster) if poster else None
                        )
                    )

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

    async def search(self, query: str) -> list[SearchResult]:
        arama_istek = await self.httpx.post(f"{self.main_url}/api/bg/searchcontent?searchterm={query}")
        decrypted   = await self.decrypt_response(arama_istek.json().get("response"))
        arama_veri  = decrypted.get("result", [])

        return [
            SearchResult(
                title  = veri.get("object_name"),
                url    = self.fix_url(f"{self.main_url}/{veri.get('used_slug')}"),
                poster = self.fix_url(veri.get("object_poster_url")),
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
        secici = HTMLParser(istek.text)

        # application/ld+json script'lerini al
        ld_json_scripts = secici.css("script[type='application/ld+json']")
        if not ld_json_scripts:
            return None

        # Son script'i al
        last_script = ld_json_scripts[-1]
        veri = loads(last_script.text(strip=True))

        title = veri.get("name")
        if alt_title := veri.get("alternateName"):
            title += f" - ({alt_title})"

        poster      = self.fix_url(veri.get("image"))
        description = veri.get("description")
        year        = veri.get("datePublished").split("-")[0]
        
        # Tags extraction from page content (h3 tag)
        tags_el = secici.css_first("div.poster.poster h3")
        tags_raw = tags_el.text(strip=True) if tags_el else ""
        tags     = [t.strip() for t in tags_raw.split(",")] if tags_raw else []

        rating = veri.get("aggregateRating", {}).get("ratingValue")
        actors = [actor.get("name") for actor in veri.get("actor", []) if actor.get("name")]

        bolumler = []
        sezonlar = veri.get("containsSeason") if isinstance(veri.get("containsSeason"), list) else [veri.get("containsSeason")]
        for sezon in sezonlar:
            episodes = sezon.get("episode")
            if isinstance(episodes, dict):
                episodes = [episodes]
            
            for bolum in episodes:
                bolumler.append(Episode(
                    season  = sezon.get("seasonNumber"),
                    episode = bolum.get("episodeNumber"),
                    title   = bolum.get("name"),
                    url     = await self.url_base_degis(bolum.get("url"), self.main_url),
                ))

        return SeriesInfo(
            url         = url,
            poster      = poster,
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            episodes    = bolumler,
            actors      = actors
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek   = await self.httpx.get(url)
        secici  = HTMLParser(istek.text)

        next_data_el = secici.css_first("script#__NEXT_DATA__")
        if not next_data_el:
            return []

        next_data   = loads(next_data_el.text(strip=True))
        secure_data = next_data.get("props", {}).get("pageProps", {}).get("secureData", {})
        decrypted   = await self.decrypt_response(secure_data)
        results     = decrypted.get("RelatedResults", {}).get("getEpisodeSources", {}).get("result", [])

        if not results:
            return []

        # Get first source (matching Kotlin)
        first_result = results[0]
        source_content = first_result.get("source_content", "")
        
        # Clean the source_content string (matching Kotlin: .replace("\"", "").replace("\\", ""))
        cleaned_source = source_content.replace('"', '').replace('\\', '')
        
        # Parse cleaned HTML
        iframe_el = HTMLParser(cleaned_source).css_first("iframe")
        iframe_src = iframe_el.attrs.get("src") if iframe_el else None
        iframe_url = self.fix_url(iframe_src) if iframe_src else None
        
        if not iframe_url:
            return []

        data = await self.extract(iframe_url, prefix=first_result.get('language_name', 'Unknown'))
        return [data] if data else []
