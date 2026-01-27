# Bu araç @keyiflerolsun tarafından | @KekikAkademi için yazılmıştır.

from KekikStream.Core  import PluginBase, MainPageResult, SearchResult, MovieInfo, ExtractResult, HTMLHelper
from Kekik.Sifreleme   import StringCodec
import json

class FullHDFilmizlesene(PluginBase):
    name        = "FullHDFilmizlesene"
    language    = "tr"
    main_url    = "https://www.fullhdfilmizlesene.tv"
    favicon     = f"https://www.google.com/s2/favicons?domain={main_url}&sz=64"
    description = "Türkiye'nin ilk ve lider HD film izleme platformu, kaliteli ve sorunsuz hizmetiyle sinema keyfini zirveye taşır."

    main_page   = {
        f"{main_url}/en-cok-izlenen-hd-filmler/"            : "En Çok izlenen Filmler",
        f"{main_url}/filmizle/aile-filmleri-hdf-izle/"      : "Aile Filmleri",
        f"{main_url}/filmizle/aksiyon-filmleri-hdf-izle/"   : "Aksiyon Filmleri",
        f"{main_url}/filmizle/animasyon-filmleri-izle/"     : "Animasyon Filmleri",
        f"{main_url}/filmizle/belgesel-filmleri-izle/"      : "Belgeseller",
        f"{main_url}/filmizle/bilim-kurgu-filmleri-izle-2/" : "Bilim Kurgu Filmleri",
        f"{main_url}/filmizle/bluray-filmler-izle/"         : "Blu Ray Filmler",
        f"{main_url}/filmizle/cizgi-filmler-fhd-izle/"      : "Çizgi Filmler",
        f"{main_url}/filmizle/dram-filmleri-hd-izle/"       : "Dram Filmleri",
        f"{main_url}/filmizle/fantastik-filmler-hd-izle/"   : "Fantastik Filmler",
        f"{main_url}/filmizle/gerilim-filmleri-fhd-izle/"   : "Gerilim Filmleri",
        f"{main_url}/filmizle/gizem-filmleri-hd-izle/"      : "Gizem Filmleri",
        f"{main_url}/filmizle/hint-filmleri-fhd-izle/"      : "Hint Filmleri",
        f"{main_url}/filmizle/komedi-filmleri-fhd-izle/"    : "Komedi Filmleri",
        f"{main_url}/filmizle/korku-filmleri-izle-3/"       : "Korku Filmleri",
        f"{main_url}/filmizle/macera-filmleri-fhd-izle/"    : "Macera Filmleri",
        f"{main_url}/filmizle/muzikal-filmler-izle/"        : "Müzikal Filmler",
        f"{main_url}/filmizle/polisiye-filmleri-izle/"      : "Polisiye Filmleri",
        f"{main_url}/filmizle/psikolojik-filmler-izle/"     : "Psikolojik Filmler",
        f"{main_url}/filmizle/romantik-filmler-fhd-izle/"   : "Romantik Filmler",
        f"{main_url}/filmizle/savas-filmleri-fhd-izle/"     : "Savaş Filmleri",
        f"{main_url}/filmizle/suc-filmleri-izle/"           : "Suç Filmleri",
        f"{main_url}/filmizle/tarih-filmleri-fhd-izle/"     : "Tarih Filmleri",
        f"{main_url}/filmizle/western-filmler-hd-izle-3/"   : "Western Filmler",
        f"{main_url}/filmizle/yerli-filmler-hd-izle/"       : "Yerli Filmler"
    }

    async def get_main_page(self, page: int, url: str, category: str) -> list[MainPageResult]:
        istek  = self.cloudscraper.get(f"{url}{page}")
        secici = HTMLHelper(istek.text)

        results = []
        for veri in secici.select("li.film"):
            title = secici.select_text("span.film-title", veri)
            href = secici.select_attr("a", "href", veri)
            poster = secici.select_attr("img", "data-src", veri)

            if title and href:
                results.append(MainPageResult(
                    category = category,
                    title    = title,
                    url      = self.fix_url(href),
                    poster   = self.fix_url(poster),
                ))

        return results

    async def search(self, query: str) -> list[SearchResult]:
        istek  = await self.httpx.get(f"{self.main_url}/arama/{query}")
        secici = HTMLHelper(istek.text)

        results = []
        for film in secici.select("li.film"):
            title  = secici.select_text("span.film-title", film)
            href   = secici.select_attr("a", "href", film)
            poster = secici.select_attr("img", "data-src", film)

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

        title       = self.clean_title(secici.select_text("div.izle-titles"))
        poster      = secici.select_poster("div img[data-src]")
        description = secici.select_text("div.ozet-ic")
        tags        = secici.select_texts("a[rel='category tag']")
        rating      = secici.regex_first(r"(\d+\.\d+|\d+)", secici.select_text("div.puanx-puan"))
        year        = secici.extract_year("div.dd a.category")
        actors      = secici.select_texts("a > span", secici.select_first("div.film-info ul li:nth-child(2)"))
        duration    = secici.regex_first(r"Süre: (\d+)\s*dk", secici.select_text("div.ozet-ic"))

        return MovieInfo(
            url         = url,
            poster      = self.fix_url(poster),
            title       = title,
            description = description,
            tags        = tags,
            rating      = rating,
            year        = year,
            actors      = actors,
            duration    = duration
        )

    async def load_links(self, url: str) -> list[ExtractResult]:
        istek  = await self.httpx.get(url)
        secici = HTMLHelper(istek.text)

        # İlk script'i al (xpath (//script)[1] yerine)
        scripts        = secici.select("script")
        script_content = scripts[0].text() if scripts else ""

        scx_json = HTMLHelper(script_content).regex_first(r"scx = (.*?);")
        if not scx_json:
            return []

        scx_data = json.loads(scx_json)
        scx_keys = list(scx_data.keys())

        link_list = []
        for key in scx_keys:
            t = scx_data[key]["sx"]["t"]
            if isinstance(t, list):
                link_list.extend(StringCodec.decode(elem) for elem in t)
            if isinstance(t, dict):
                link_list.extend(StringCodec.decode(v) for k, v in t.items())

        response = []
        for link in link_list:
            data = await self.extract(self.fix_url(link))
            if data:
                response.append(data)

        return response
