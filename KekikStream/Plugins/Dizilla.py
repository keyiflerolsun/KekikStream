# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core import kekik_cache, PluginBase, MainPageResult, SearchResult, SeriesInfo, Episode
from parsel           import Selector
from json             import loads
from urllib.parse     import urlparse, urlunparse
from Crypto.Cipher    import AES
from base64           import b64decode

class Dizilla(PluginBase):
    name        = "Dizilla"
    language    = "tr"
    main_url    = "https://dizilla40.com"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Dizilla tüm yabancı dizileri ücretsiz olarak Türkçe Dublaj ve altyazılı seçenekleri ile 1080P kalite izleyebileceğiniz yeni nesil yabancı dizi izleme siteniz."

    main_page   = {
        f"{main_url}/tum-bolumler"          : "Altyazılı Bölümler",
        f"{main_url}/dizi-turu/aile"        : "Aile",
        f"{main_url}/dizi-turu/aksiyon"     : "Aksiyon",
        f"{main_url}/dizi-turu/bilim-kurgu" : "Bilim Kurgu",
        f"{main_url}/dizi-turu/romantik"    : "Romantik",
        f"{main_url}/dizi-turu/komedi"      : "Komedi"
    }

    #@kekik_cache(ttl=60*60)
    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)

        ana_sayfa = []

        if "dizi-turu" in url:
            ana_sayfa.extend([
                MainPageResult(
                    category = category,
                    title    = veri.css("span.font-normal::text").get(),
                    url      = self.fix_url(veri.css("a::attr(href)").get()),
                    poster   = self.fix_url(veri.css("img::attr(src)").get() or veri.css("img::attr(data-src)").get())
                )
                    for veri in secici.css("span.watchlistitem-")
            ])
        else:
            for veri in secici.css("div.tab-content > div.grid a"):
                name    = veri.css("h2::text").get()
                ep_name = veri.xpath("normalize-space(//div[contains(@class, 'opacity-80')])").get()
                if not ep_name:
                    continue

                ep_name = ep_name.replace(". Sezon", "x").replace(". Bölüm", "").replace("x ", "x")
                title   = f"{name} - {ep_name}"

                ep_req    = await self.httpx.get(self.fix_url(veri.css("::attr(href)").get()))
                ep_secici = Selector(ep_req.text)
                href      = self.fix_url(ep_secici.css("nav li:nth-of-type(3) a::attr(href)").get())
                poster    = self.fix_url(ep_secici.css("img.imgt::attr(src)").get())

                ana_sayfa.append(
                    MainPageResult(
                        category = category,
                        title    = title,
                        url      = href,
                        poster   = poster
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

    #@kekik_cache(ttl=60*60)
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

    #@kekik_cache(ttl=60*60)
    async def url_base_degis(self, eski_url:str, yeni_base:str) -> str:
        parsed_url       = urlparse(eski_url)
        parsed_yeni_base = urlparse(yeni_base)
        yeni_url         = parsed_url._replace(
            scheme = parsed_yeni_base.scheme,
            netloc = parsed_yeni_base.netloc
        )

        return urlunparse(yeni_url)

    #@kekik_cache(ttl=60*60)
    async def load_item(self, url: str) -> SeriesInfo:
        istek  = await self.httpx.get(url)
        secici = Selector(istek.text)
        veri   = loads(secici.xpath("//script[@type='application/ld+json']/text()").getall()[-1])

        title       = veri.get("name")
        if alt_title := veri.get("alternateName"):
            title += f" - ({alt_title})"

        poster      = self.fix_url(veri.get("image"))
        description = veri.get("description")
        year        = veri.get("datePublished").split("-")[0]
        
        # Tags extraction from page content (h3 tag)
        tags_raw = secici.css("h3.text-white.opacity-60::text").get()
        tags     = [t.strip() for t in tags_raw.split(",")] if tags_raw else []

        rating      = veri.get("aggregateRating", {}).get("ratingValue")
        actors      = [actor.get("name") for actor in veri.get("actor", []) if actor.get("name")]

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

    #@kekik_cache(ttl=15*60)
    async def load_links(self, url: str) -> list[dict]:
        istek   = await self.httpx.get(url)
        secici  = Selector(istek.text)

        next_data   = loads(secici.css("script#__NEXT_DATA__::text").get())
        secure_data = next_data.get("props", {}).get("pageProps", {}).get("secureData", {})
        decrypted   = await self.decrypt_response(secure_data)
        results     = decrypted.get("RelatedResults", {}).get("getEpisodeSources", {}).get("result", [])

        links = []
        for result in results:
            iframe_src = Selector(result.get("source_content")).css("iframe::attr(src)").get()
            iframe_url = self.fix_url(iframe_src)
            if not iframe_url:
                continue

            extractor = self.ex_manager.find_extractor(iframe_url)
            links.append({
                "url"  : iframe_url,
                "name" : f"{extractor.name if extractor else 'Main Player'} | {result.get('language_name')}",
            })

        return links